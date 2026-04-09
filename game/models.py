from django.db import models

# Create your models here.
import random
from django.contrib.auth.models import User

JOIN_CODE_CHARS = "ABCDEFGHJKLMNPQRSTUVWXYZ346789abdgjmnpqrt"
JOIN_CODE_LENGTH = 6



def generate_join_code():
    code = "".join(random.choice(JOIN_CODE_CHARS) for _ in range(JOIN_CODE_LENGTH))
    while Game.objects.filter(join_code=code).exists():
        code = "".join(random.choice(JOIN_CODE_CHARS) for _ in range(JOIN_CODE_LENGTH))
    return code


class Player(models.Model):
    handle = models.CharField(max_length=255, blank=True)
    # user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True) # if a user may have only 1 Player
    
    # Allowing multiple Players per User for flexibility in testing and gameplay
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True) 

    def __str__(self):
        if self.user:
            return self.user.username
        return self.handle

class GameManager(models.Manager):
    def create_game(self, creator):
        game = self.create(creator=creator)
        GameState.objects.create(game=game, state_data={"board_state": [None] * 9})
        game = self.get(id=game.id)  # Refresh game instance to include the new state
        return game

class Game(models.Model):
    creator = models.ForeignKey(
        Player, on_delete=models.CASCADE, related_name="created_games"
    )
    opponent = models.ForeignKey(
        Player, on_delete=models.CASCADE, related_name="joined_games", null=True, blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    join_code = models.CharField(
        max_length=JOIN_CODE_LENGTH, default=generate_join_code, unique=True
    )
    in_progress = models.BooleanField(default=True)
    objects = GameManager()

class GameState(models.Model):
    game = models.ForeignKey(Game, on_delete=models.CASCADE, related_name="states")

    # state_data will be an object that fields:
    # board_state: array of 9 elements, each being null, "X", or "O"
    state_data = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)