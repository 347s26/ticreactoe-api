from django.contrib import admin

from game.models import Game, GameState, Player

# Register your models here.
admin.site.register(Player)
admin.site.register(Game)
admin.site.register(GameState)