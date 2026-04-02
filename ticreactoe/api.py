from django.shortcuts import get_object_or_404
from ninja import ModelSchema, NinjaAPI

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