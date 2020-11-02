from django.contrib import admin
from .models import Team, Player, Game, Team_Game_Map, Player_Game_Stats

# Register your models here.

admin.site.register(Team)
admin.site.register(Player)
admin.site.register(Game)
admin.site.register(Team_Game_Map)
admin.site.register(Player_Game_Stats)
