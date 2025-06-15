import math
import pandas as pd
import re
from typing import Any, Dict, List

from .yahoo_normalizer import YahooNormalizer
from ....sports.normalizers import BaseballNormalizer


#############################################################################################
#############################################################################################

atbat_tokens = {

    "struck out": 0,
    "strikes out": 0,
    "called out on strikes": 0,

    "fouled out": 1,
    "fouls out": 1,
    
    "flied out": 2,
    "flies out": 2,
    "flied into double play": 2,
    "flied into triple play": 2,

    "grounded out": 3,
    "grounds out": 3,
    "grounded into double play": 3,
    "grounded into triple play": 3,
    "hit into fielder's choice": 3,
    "reached on fielder's choice": 3,
    "reaches on a fielder's choice": 3,
    r"reached on \[\w+\.\w+\.\d+\]'s \w+ error": 3,
    "reaches on error": 3,
    
    "popped out": 4,
    "pops out": 4,
    "popped into double play": 4,

    "lined out": 5,
    "lines out": 5,
    "lined into triple play": 5,
    "lined into double play": 5,

    "hit by pitch": 6,
    
    "walked": 7,
    "walks": 7,

    "reached on an infield single": 8, 
    "singled": 8,
    "singles": 8,

    "doubled": 9,
    "doubles": 9,              
    "ground rule double": 9,

    "tripled": 10,
    "triples": 10,

    "homered": 11,
    "homers": 11,
    "hit an inside the park home run": 11,
}


token_skip = [
    "unknown into double play",
    "On initial placement",
    "was skipped",
    "batted out of order",
    "out on batter's interference",
    "reached on catcher's interference",
     
    "bunt",
    "wild pitch",
    "sacrifice fly",
    "sacrificed",

]

def find_matching_token(input_string):
    """
    Searches for a token string from a list of tokens within the input string.
    Returns the first matching token string, or None if no match is found.
    """
    for token in atbat_tokens:
        # Use re.search to look for the token as a substring
        # Escape the token to handle any special regex characters
        if re.search(token, input_string):
            return atbat_tokens[token]
    return None



#############################################################################################
#############################################################################################



class YahooMLBNormalizer(BaseballNormalizer, YahooNormalizer):
    """Normalizer for Yahoo Baseball data (MLB)."""

    def __init__(self, leagueId: str):
        super().__init__("MLB", "sport_baseball")


    def _set_atbats(self, webData):
        gameData = webData["gameData"]
        gameId = gameData["gameid"]

        batterTeam = {}
        pitcherTeam = {}
        for playerId, teamId, _ in self._set_player_list(webData, "B"):
            batterTeam[playerId.split(".")[-1]] = teamId
        for playerId, teamId, _ in self._set_player_list(webData, "P"):
            pitcherTeam[playerId.split(".")[-1]] = teamId

        atBats = []
        try:
            for row in [value for value in gameData["play_by_play"].values() if value["play_type"] == "RESULT"]:
            
                result = find_matching_token(row["text"])
                if result is not None:
                    atBats.append({
                        "game_id": gameId,
                        "team_id": batterTeam[row["batter"]],
                        "opp_id": pitcherTeam[row["pitcher"]],
                        "play_num": int((int(row['play_num']) - 1)/100),
                        "pitcher_id": f"mlb.p.{row['pitcher']}",
                        "batter_id": f"mlb.p.{row['batter']}",
                        "at_bat_type_id": result,
                        "hit_hardness": row.get("hit_hardness"),
                        "hit_style":  row.get("hit_style"),
                        "hit_angle":  row.get("hit_angle"),
                        "hit_distance": row.get("hit_distance"),
                        "period": row["period"]
                    })
        except KeyError:
            pass
            # print(f"Skipping {gameId}: No AtBat data")
        return atBats


    def _set_pitches(self, webData):
        gameData = webData["gameData"]
        gameId = gameData["gameid"]

        batterTeam = {}
        pitcherTeam = {}
        for playerId, teamId, _ in self._set_player_list(webData, "B"):
            batterTeam[playerId.split(".")[-1]] = teamId
        for playerId, teamId, _ in self._set_player_list(webData, "P"):
            pitcherTeam[playerId.split(".")[-1]] = teamId
        
        pitches = []
        try:
            for row in [value for value in gameData["pitches"].values()]:
                try:
                    pitches.append({
                        "game_id": gameId,
                        "play_num": row["play_num"],
                        "pitcher_id": f"mlb.p.{row['pitcher']}",
                        "batter_id": f"mlb.p.{row['batter']}",
                        "pitch_type_id": row['pitch_type'],
                        "pitch_result_id": row['result'],
                        "period": row['period'],
                        "sequence": row['sequence'],
                        "balls": row['balls'],
                        "strikes": row['strikes'],
                        "vertical": row['vertical'],
                        "horizontal": row['horizontal'],
                        "velocity": row['velocity']
                    })
                except KeyError:
                    pass
        except KeyError as e:
            pass
            # print(f"Skipping {gameId}: No pitch data   Key Error: {e}")
        return pitches




    def _set_player_list(self, data: dict, B_P: str) -> List:
        gameData = data["gameData"]
        gameId = gameData["gameid"]
        
        teamIds = {"away": gameData["away_team_id"], "home": gameData["home_team_id"]}
        oppIds = {"away": teamIds["home"], "home": teamIds["away"]}

        playerList = []
        for a_h in ("away", "home"):
            try:
                for value in gameData["lineups"][f"{a_h}_lineup"][B_P].values():
                    playerList.append((value["player_id"], teamIds[a_h], oppIds[a_h]))
            except (KeyError, TypeError) as e:
                pass
        return playerList



    def _set_batter_stats(self, webData):
        gameData = webData["gameData"]
        gameId = gameData["gameid"]
        teamIds = {"away": gameData["away_team_id"], "home": gameData["home_team_id"]}
        oppIds = {"away": teamIds["home"], "home": teamIds["away"]}

        playerStats=[]
        # for playerId, teamId, oppId in self._set_player_list(webData, "B"):
        #     try:
        #         raw_player_data = webData["StatsStore"]["playerStats"][playerId]['mlb.stat_variation.2']
        #     except (KeyError, AttributeError):
        #         raw_player_data = None

        #     if raw_player_data :
        #         try:
        #             newPlayerStats = self._BatterStats(
        #                 player_id=playerId,
        #                 game_id=gameId,
        #                 team_id=teamId,
        #                 opp_id=oppId,
        #                 ab = raw_player_data["mlb.stat_type.2"],
        #                 bb = raw_player_data["mlb.stat_type.14"],
        #                 r = raw_player_data["mlb.stat_type.3"],
        #                 h = raw_player_data["mlb.stat_type.4"],
        #                 sb = raw_player_data["mlb.stat_type.12"],
        #                 rbi = raw_player_data["mlb.stat_type.8"],
        #                 so = raw_player_data["mlb.stat_type.17"]   
        #             )                 
        #             playerStats.append(newPlayerStats)
        #         except (IndexError, KeyError):
        #             pass
        return playerStats

 


    def _set_pitcher_stats(self, webData):
        gameData = webData["gameData"]
        gameId = gameData["gameid"]
        teamIds = {"away": gameData["away_team_id"], "home": gameData["home_team_id"]}
        oppIds = {"away": teamIds["home"], "home": teamIds["away"]}

        playerStats = []
        # for playerId, teamId, oppId in self._set_player_list(webData, "P"):
        #     try:
        #         raw_player_data = webData["StatsStore"]["playerStats"][playerId]['mlb.stat_variation.2']
        #     except (KeyError, AttributeError):
        #         raw_player_data = None

        #     if raw_player_data :
        #         try:
        #             newPlayerStats = self._PitcherStats(
        #                 player_id=playerId,
        #                 game_id=gameId,
        #                 team_id=teamId,
        #                 opp_id=oppId,
        #                 full_ip = raw_player_data["mlb.stat_type.139"].split(".")[0],
        #                 partial_ip = raw_player_data["mlb.stat_type.139"].split(".")[1],
        #                 bba = raw_player_data["mlb.stat_type.118"],
        #                 ha = raw_player_data["mlb.stat_type.111"],
        #                 ra = raw_player_data["mlb.stat_type.113"],
        #                 er = raw_player_data["mlb.stat_type.114"],
        #                 k = raw_player_data["mlb.stat_type.121"],
        #                 hra = raw_player_data["mlb.stat_type.115"],
        #                 w = raw_player_data["mlb.stat_type.101"],
        #                 l = raw_player_data["mlb.stat_type.102"],
        #                 sv = raw_player_data["mlb.stat_type.107"],
        #                 blsv = raw_player_data["mlb.stat_type.147"] 
        #             )                 
        #             playerStats.append(newPlayerStats)
        #         except (IndexError, KeyError):
        #             pass
        return playerStats




    def _set_batting_order(self, webData):
        gameData = webData["gameData"]
        gameId = gameData["gameid"]
        teamIds = {"away": gameData["away_team_id"], "home": gameData["home_team_id"]}
        oppIds = {"away": teamIds["home"], "home": teamIds["away"]}

        battingOrder = []
        try:
            for a_h in ("away", "home"):
                for lineup in gameData["lineups"][f"{a_h}_lineup"]["B"].values():
                    battingOrder.append({
                        "game_id": gameId,
                        "player_id": lineup["player_id"],
                        "team_id": teamIds[a_h],
                        "opp_id": oppIds[a_h],
                        "batt_order": lineup["order"],
                        "sub_order": lineup["suborder"],
                        "pos": lineup["position"]
                    })
        except TypeError:
            pass
        return battingOrder


    def _set_bullpen(self, webData):
        gameData = webData["gameData"]
        gameId = gameData["gameid"]
        teamIds = {"away": gameData["away_team_id"], "home": gameData["home_team_id"]}
        oppIds = {"away": teamIds["home"], "home": teamIds["away"]}

        pitchingOrder = []
        try:
            for a_h in ("away", "home"): 
                for bulpen in gameData["lineups"][f"{a_h}_lineup"]["P"].values():
                    pitchingOrder.append({
                        "game_id": gameId,
                        "player_id": bulpen["player_id"],
                        "team_id": teamIds[a_h],
                        "opp_id": oppIds[a_h],
                        "pitch_order": bulpen["order"]
                })
        except TypeError:
            pass
        return pitchingOrder


    def _set_lineups(self, webData):
        lineups = {}
        try:
            lineups["batting"] = self._set_batting_order(webData)
            lineups["pitching"] = self._set_bullpen(webData)
        except KeyError:
            # self.logger.warning("No lineups")
            pass
        return lineups


    def _set_player_stats(self, webData):
        playerStats = [] 
        # [playerStats.append(batRecord) for batRecord in self._set_batter_stats(webData)] 
        # [playerStats.append(pitchRecord) for pitchRecord in self._set_pitcher_stats(webData)] 
        return playerStats


    def _set_misc(self, webData):
        misc = {"at_bats": self._set_atbats(webData),
                "pitches": self._set_pitches(webData)}
        return misc


    def _set_team_stats(self, data: Dict[str, Any]) -> List["BaseballTeamStat"]:
        gameData = data["gameData"]
        gameId = gameData["gameid"]
        teamIds = {"away": gameData["away_team_id"], "home": gameData["home_team_id"]}
        oppIds = {"away": teamIds["home"], "home": teamIds["away"]}

        teamStats = []
        # try:
        #     for a_h in ("away", "home"):
        #         raw_stat_data = data["StatsStore"]["teamStatsByGameId"][gameId][teamIds[a_h]]['mlb.stat_variation.2']           

        #         newTeamStats = self._TeamStats(
        #             game_id=gameId,
        #             team_id=teamIds[a_h],
        #             opp_id=oppIds[a_h],
        #             ab = raw_stat_data["mlb.stat_type.406"],
        #             bb = raw_stat_data["mlb.stat_type.415"],
        #             r = raw_stat_data["mlb.stat_type.402"],
        #             h = raw_stat_data["mlb.stat_type.403"],
        #             hr = raw_stat_data["mlb.stat_type.404"],
        #             rbi = raw_stat_data["mlb.stat_type.405"],
        #             sb = raw_stat_data["mlb.stat_type.409"],
        #             lob = raw_stat_data["mlb.stat_type.416"],
        #             full_ip = raw_stat_data["mlb.stat_type.512"].split(".")[0],
        #             partial_ip = raw_stat_data["mlb.stat_type.512"].split(".")[1],
        #             bba = raw_stat_data["mlb.stat_type.503"],
        #             ha = raw_stat_data["mlb.stat_type.502"],
        #             ra = raw_stat_data["mlb.stat_type.505"],
        #             hra = raw_stat_data["mlb.stat_type.507"],
        #             er = raw_stat_data["mlb.stat_type.506"],
        #             k = raw_stat_data["mlb.stat_type.504"]
        #         )
        #         teamStats.append(newTeamStats)
        # except KeyError:
        #     pass
        return teamStats  

