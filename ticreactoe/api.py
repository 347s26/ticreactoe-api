from django.shortcuts import get_object_or_404
from ninja import ModelSchema, NinjaAPI, Schema
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

from game.models import Game, GameState, Player

api = NinjaAPI()

class PlayerSchema(ModelSchema):
    class Meta:
        model = Player
        fields = ["id", "handle"]

class GameSchema(ModelSchema):
    creator: PlayerSchema
    opponent: PlayerSchema | None = None
    class Meta:
        model = Game
        fields = ["creator", "opponent", "created_at", "join_code", "in_progress"]

class PlayerDetailSchema(ModelSchema):
    created_games: list[GameSchema] = []
    joined_games: list[GameSchema] = []
    class Meta:
        model = Player
        fields = ["id", "handle"]

@api.get('/player/{handle}', response=PlayerDetailSchema)
def get_player(request, handle: str):
    if request.user.is_authenticated:
        player, _ = Player.objects.get_or_create(handle=handle)
        return player
    return get_object_or_404(Player, handle=handle)

@api.post('/player/{handle}')
def create_player(request, handle: str):
    player, created = Player.objects.get_or_create(handle=handle)
    if created:
        return {"message": f"Player '{handle}' created."}
    return {"message": f"Player '{handle}' already exists."}

@api.post('/player/{handle}/game', response=GameSchema)
def create_game(request, handle: str):
    player = get_object_or_404(Player, handle=handle)
    game = Game.objects.create_game(creator=player)
    return game

@api.post('/game/{join_code}/join', response=GameSchema)
def join_game(request, join_code: str, handle: str):
    game = get_object_or_404(Game, join_code=join_code)
    if not game.in_progress:
        return {"error": "Game is already completed."}
    if game.opponent:
        return {"error": "Game already has an opponent."}
    player = Player.objects.get_or_create(handle=handle)[0]
    game.opponent = player
    game.save()
    return game

@api.post('/player/{handle}/game/{join_code}/join', response=GameSchema)
def player_join_game(request, handle: str, join_code: str):
    return join_game(request, join_code=join_code, handle=handle)


class GameStateSchema(ModelSchema):
    class Meta:
        model = GameState
        fields = ["game", "state_data", "created_at"]

class GameAndStateSchema(ModelSchema):
    creator: PlayerSchema
    opponent: PlayerSchema | None = None
    states: list[GameStateSchema] = []
    class Meta:
        model = Game
        fields = ["creator", "opponent", "created_at", "join_code", "in_progress"]

@api.get('/player/{handle}/game/{join_code}', response=GameAndStateSchema)
def get_game_state(request, handle: str, join_code: str):
    game = get_object_or_404(Game, join_code=join_code)
    if game.creator.handle != handle and (not game.opponent or game.opponent.handle != handle):
        return {"error": "Player is not part of this game."}
    return game

WIN_LINES = [
    [0, 1, 2], [3, 4, 5], [6, 7, 8],
    [0, 3, 6], [1, 4, 7], [2, 5, 8],
    [0, 4, 8], [2, 4, 6],
]


def _serialize_game(game):
    """Return a plain dict matching GameAndStateSchema for WebSocket broadcast."""
    return {
        "join_code": game.join_code,
        "in_progress": game.in_progress,
        "created_at": game.created_at.isoformat(),
        "creator": {"id": game.creator.id, "handle": game.creator.handle},
        "opponent": (
            {"id": game.opponent.id, "handle": game.opponent.handle}
            if game.opponent else None
        ),
        "states": [
            {"state_data": s.state_data, "created_at": s.created_at.isoformat()}
            for s in game.states.order_by("created_at")
        ],
    }

class MoveSchema(Schema):
    cell_index: int

@api.post('/player/{handle}/game/{join_code}/move', response=GameAndStateSchema)
def make_move(request, handle: str, join_code: str, data: MoveSchema):
    game = get_object_or_404(Game, join_code=join_code)

    if not game.in_progress:
        return api.create_response(request, {"error": "Game is not in progress."}, status=400)
    if game.opponent is None:
        return api.create_response(request, {"error": "Game has no opponent yet."}, status=400)

    if game.creator.handle == handle:
        symbol = "X"
    elif game.opponent.handle == handle:
        symbol = "O"
    else:
        return api.create_response(request, {"error": "Player is not part of this game."}, status=403)

    current_state = game.states.order_by("created_at").last()
    board = list(current_state.state_data["board_state"])

    cell_index = data.cell_index
    if not (0 <= cell_index <= 8):
        return api.create_response(request, {"error": "Invalid cell index."}, status=400)

    # Toggle own mark off; overwrite opponent's mark; place on empty cell
    board[cell_index] = None if board[cell_index] == symbol else symbol
    GameState.objects.create(game=game, state_data={"board_state": board})

    won = any(board[a] == board[b] == board[c] == symbol for a, b, c in WIN_LINES)
    draw = not won and all(cell is not None for cell in board)
    if won or draw:
        game.in_progress = False
        game.save()

    game.refresh_from_db()

    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f"game_{join_code}",
        {"type": "game.update", "data": _serialize_game(game)},
    )

    return game

# I was getting carried away. let's not complicate it yet
# @api.get('/player/{handle}/game/{join_code}/observe', response=GameSchema)
# def observe_game_from_perspective(request, handle: str, join_code: str):
#     game = get_object_or_404(Game, join_code=join_code)
#     if game.creator.handle != handle and (not game.opponent or game.opponent.handle != handle):
#         return {"error": "Player is not part of this game."}
#     return game

# @api.get('/game/{join_code}/observe', response=GameSchema)
# def observe_game(request, join_code: str):
#     game = get_object_or_404(Game, join_code=join_code)
#     return game