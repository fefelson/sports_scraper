import math
from typing import Any, Dict, List

from .yahoo_normalizer import YahooNormalizer
from ....sports.normalizers import BasketballNormalizer


#############################################################################################
#############################################################################################



class YahooBasketballNormalizer(BasketballNormalizer, YahooNormalizer):
    """Normalizer for Yahoo Basketball data (NBA and NCAAB)."""

    def __init__(self, leagueId: str):
        super().__init__(leagueId.upper(), "sport_basketball")

        # League-specific settings
        self._base_minutes = 48 if self.leagueId == "NBA" else 40
        self._regulation_periods = 4 if self.leagueId == "NBA" else 2
        self._id_prefix = "nba" if self.leagueId == "NBA" else "ncaab"
        self._stat_variation = f"{self._id_prefix}.stat_variation.2"


    def _set_linueups(self, webData):
        return None 
    

    def _set_misc(self, webData):
        gameId = webData["PageStore"]["pageData"]["entityId"]
        gameData = webData["GamesStore"]["games"][gameId]
        try:
            playerShots = self._set_player_shots(gameData)
        except:
            playerShots = None
        return playerShots
    

    def _set_player_shots(self, data: Dict[str, Any]) -> List["BasketballShot"]:
        gameId = data["gameid"]
        teamIds = {"away": data["away_team_id"], "home": data["home_team_id"]}

        playerShots = []
        for shot in [shot for shot in data["play_by_play"].values()
                     if shot["class_type"] == "SHOT" and (int(shot["type"]) not in range(10, 25) or (int(shot["points"])==1 and int(shot["period"]) >= self._regulation_periods and  self._calculate_clutch(shot)))]:
            base_pct = float(shot["baseline_offset_percentage"])
            side_pct = float(shot["sideline_offset_percentage"])
            base_pct_adjusted = base_pct * ((-1) ** int(shot["side_of_basket"] == "R"))
            distance = int(math.sqrt((50 * base_pct_adjusted) ** 2 + (side_pct * 94) ** 2))

            newShot = self._PlayerShots(
                player_id=f"{self._id_prefix}.p.{shot['player']}",
                team_id=f"{self._id_prefix}.t.{shot['team']}",
                opp_id=teamIds["home"] if int(teamIds["home"].split(".")[-1]) != int(shot["team"]) else teamIds["away"],
                game_id=gameId,
                period=shot["period"],
                shot_type_id=shot["type"],
                assist_id=None if int(shot["assister"]) == 0 else f"{self._id_prefix}.p.{shot['assister']}",
                shot_made=shot["shot_made"],
                points=int(shot["points"]),
                base_pct=base_pct,
                side_pct=side_pct,
                distance=distance,
                fastbreak=shot["fastbreak"],
                side_of_basket=shot["side_of_basket"],
                clutch=(False if int(shot["period"]) < self._regulation_periods 
                        else self._calculate_clutch(shot)),
                zone=self._get_shot_zone(shot)
            )
            playerShots.append(newShot)
        return playerShots
    

    def _set_player_stats(self, data: Dict[str, Any]) -> List["BasketballPlayerStat"]:
        gameId = data["PageStore"]["pageData"]["entityId"]
        gameData = data["GamesStore"]["games"][gameId]

        playerStats = []
        try:
            starters = [posRecord["player_id"] for a_h in ("away", "home")
                        for posRecord in gameData["lineups"]["{}_lineup".format(a_h)]["all"].values()
                        if int(posRecord["starter"]) == 1]
        except (AttributeError, TypeError):
            starters = []

        for playerId, teamId, oppId in self._set_player_stats_list(gameData):
            try:
                raw_player_data = data["StatsStore"]["playerStats"][playerId][self._stat_variation]
                mins = f"{(t := raw_player_data.get(f'{self._id_prefix}.stat_type.3', '0:0').split(':'))[0]}.{int((int(t[1]) / 60) * 100 + 0.5) if len(t) > 1 else 0}"
            except (KeyError, AttributeError):
                raw_player_data = None
                mins = 0

            if raw_player_data and float(mins) > 0:
                try:
                    newPlayerStats = self._PlayerStats(
                        player_id=playerId,
                        game_id=gameId,
                        team_id=teamId,
                        opp_id=oppId,
                        starter=(playerId in starters),
                        minutes=mins,
                        fgm=raw_player_data[f"{self._id_prefix}.stat_type.28"].split("-")[0],
                        fga=raw_player_data[f"{self._id_prefix}.stat_type.28"].split("-")[1],
                        ftm=raw_player_data[f"{self._id_prefix}.stat_type.29"].split("-")[0],
                        fta=raw_player_data[f"{self._id_prefix}.stat_type.29"].split("-")[1],
                        tpm=raw_player_data[f"{self._id_prefix}.stat_type.30"].split("-")[0],
                        tpa=raw_player_data[f"{self._id_prefix}.stat_type.30"].split("-")[1],
                        pts=raw_player_data[f"{self._id_prefix}.stat_type.13"],
                        oreb=raw_player_data[f"{self._id_prefix}.stat_type.14"],
                        dreb=raw_player_data[f"{self._id_prefix}.stat_type.15"],
                        ast=raw_player_data[f"{self._id_prefix}.stat_type.17"],
                        stl=raw_player_data[f"{self._id_prefix}.stat_type.18"],
                        blk=raw_player_data[f"{self._id_prefix}.stat_type.19"],
                        turnovers=raw_player_data[f"{self._id_prefix}.stat_type.20"],
                        fouls=raw_player_data[f"{self._id_prefix}.stat_type.22"],
                        plus_minus=raw_player_data.get(f"{self._id_prefix}.stat_type.32") if self.leagueId == "NBA" else None
                    )
                    playerStats.append(newPlayerStats)
                except IndexError:
                    pass
        return playerStats
    

    def _set_team_stats(self, data: Dict[str, Any]) -> List["BasketballTeamStat"]:
        gameId = data["PageStore"]["pageData"]["entityId"]
        gameData = data["GamesStore"]["games"][gameId]
        teamIds = {"away": gameData["away_team_id"], "home": gameData["home_team_id"]}
        oppIds = {"away": teamIds["home"], "home": teamIds["away"]}

        teamStats = []
        for a_h in ("away", "home"):
            raw_stat_data = data["StatsStore"]["teamStatsByGameId"][gameId][teamIds[a_h]][self._stat_variation]
            # Adjust minutes for overtime: base + (extra periods * 5)
            minutes = self._base_minutes + (len(gameData["game_periods"]) - self._regulation_periods) * 5
            try:
                pts_in_pt = sum(
                    int(x["points"]) * int(x["shot_made"])
                    for x in gameData["play_by_play"].values()
                    if x["class_type"] == "SHOT" and x["team"] == teamIds[a_h].split(".")[-1]
                    and float(x["sideline_offset_percentage"]) <= 0.15
                    and float(x["baseline_offset_percentage"]) <= 0.4
                )
            except KeyError:
                pts_in_pt = None

            newTeamStats = self._TeamStats(
                game_id=gameId,
                team_id=teamIds[a_h],
                opp_id=oppIds[a_h],
                minutes=minutes,
                fga=raw_stat_data[f"{self._id_prefix}.stat_type.128"].split("-")[1],
                fgm=raw_stat_data[f"{self._id_prefix}.stat_type.128"].split("-")[0],
                fta=raw_stat_data[f"{self._id_prefix}.stat_type.129"].split("-")[1],
                ftm=raw_stat_data[f"{self._id_prefix}.stat_type.129"].split("-")[0],
                tpa=raw_stat_data[f"{self._id_prefix}.stat_type.130"].split("-")[1],
                tpm=raw_stat_data[f"{self._id_prefix}.stat_type.130"].split("-")[0],
                pts=raw_stat_data[f"{self._id_prefix}.stat_type.113"],
                oreb=raw_stat_data[f"{self._id_prefix}.stat_type.114"],
                dreb=raw_stat_data[f"{self._id_prefix}.stat_type.115"],
                ast=raw_stat_data[f"{self._id_prefix}.stat_type.117"],
                stl=raw_stat_data[f"{self._id_prefix}.stat_type.118"],
                blk=raw_stat_data[f"{self._id_prefix}.stat_type.119"],
                turnovers=raw_stat_data[f"{self._id_prefix}.stat_type.120"],
                fouls=raw_stat_data[f"{self._id_prefix}.stat_type.122"],
                pts_in_pt=pts_in_pt
            )
            teamStats.append(newTeamStats)
        return teamStats  

