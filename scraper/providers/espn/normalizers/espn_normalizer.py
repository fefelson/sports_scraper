from copy import deepcopy
from datetime import datetime
from typing import List, Any, Dict
import pytz

from ....capabilities.normalizeable import NormalAgent
from ....utils.logging_manager import get_logger

# for debugging
from pprint import pprint

##########################################################################
##########################################################################


est = pytz.timezone('America/New_York')


##########################################################################
##########################################################################


class ESPNNormalizer(NormalAgent):
    """ normalizer for ESPN data."""

    def __init__(self, leagueId: str, sportId: str):

        self.leagueId = leagueId
        self.sportId = sportId
        self.logger = get_logger()


    # ['gmStrp', 'gmInfo', 'shtChrt', 'gmStry',''scrSumm', 'lnScr', 'plys', 'wnPrb', 'bxscr']
    # ['pbp']

    def normalize_boxscore(self, webData: dict) -> dict:      
        # pprint(webData)
        # self.logger.debug("Normalize ESPN boxscore")

        return {
            "game": self._set_game_info(webData["box"]["gmStrp"]),
            "teamStats": self._set_team_stats(webData["box"]),
            "playerStats": self._set_player_stats(webData["box"]["bxscr"]),
            "stadium": self._set_stadium(webData["box"]["gmInfo"]),
            "misc": self._set_misc(webData),
            "teams": self._set_teams(webData["box"]),
            "players": self._set_players(webData["box"]["bxscr"])
        }   


    def normalize_matchup(self, webData: dict) -> dict:
        # pprint(webData)
        self.logger.debug("Normalize ESPN matchup")
        raise NotImplementedError


    def normalize_player(self, webData: dict) -> dict:
        # pprint(webData)
        self.logger.debug("Normalize ESPN player")
        raise NotImplementedError      


    def normalize_scoreboard(self, webData: dict) -> dict:
        # pprint(webData)
        self.logger.debug("Normalize ESPN scoreboard")
        games = []
        for game in webData["page"]["content"]["scoreboard"]["evts"]:  

            games.append({
                "provider": "espn",
                "gameId": game["id"],
                "leagueId": self.leagueId,
                "homeId": game["teams"][0]["id"],
                "awayId": game["teams"][1]["id"], 
                "url": game['link'],
                "gameTime": str(datetime.fromisoformat(game["date"].replace("Z", "+00:00")).astimezone(est)), 
                "season": webData["page"]["content"]["scoreboard"]["season"]["displayName"].split("-")[0],
                "week": game.get("week", None),
                "statusType": game["status"]["description"].lower(),
                "gameType": game.get("note").lower() if game.get("note") else None,
            })
                            
        return {"provider": "espn",
                "league_id": self.leagueId,
                "games": games
                }   

    
    def normalize_team(self, raw_data: dict) -> "Team":
        self.logger.debug("Normalize ESPN team")
        raise NotImplementedError


    def _set_game_info(self, game: Dict[str, Any]) -> dict: 
        # pprint(game)

        zeroIsHome = game["tms"][0]['isHome']
        return {
            "league_id": self.leagueId,
            "game_id": game["gid"],
            "home_id": f"{self.leagueId.lower()}.t.{game['tms'][0 if zeroIsHome else 1]['id']}",
            "away_id": f"{self.leagueId.lower()}.t.{game['tms'][1 if zeroIsHome else 0]['id']}",
            "game_date": str(datetime.fromisoformat(game["dt"].replace("Z", "+00:00")).astimezone(est))
        }

    
    def _set_misc(self, webData: dict) -> Any:
        raise NotImplementedError


    def _set_players(self, data: dict) -> List[dict]:
        # pprint(data)
        players = []
        for player in [ath["athlt"] for team in data for r in team["stats"] for ath in r['athlts']]:
            players.append(player)
        
        return players  


    def _set_player_stats(self, data: dict) -> List[dict]:
        raise NotImplementedError


    def _set_stadium(self, data: Dict[str, Any]) -> dict:
        # pprint(data)
        
        return {"name": data["loc"]} if data.get("loc") else None


    def _set_teams(self, data: dict) -> List[dict]:
        # pprint(data)

        teams = []
        for team in data["gmStrp"]["tms"]:

            roster = data["bxscr"][0]['stats'] if data["bxscr"][0]["tm"]["id"] == team["id"] else data["bxscr"][1]['stats']
            team["displayName"] = "Cleveland Guardians" if team["displayName"] == "Cleveland Indians" else team["displayName"]
            teams.append({
                "team_id": f"{self.leagueId.lower()}.t.{team['id']}",
                "abrv": team["abbrev"],
                "displayName": team["displayName"],
                "primary_color": team["teamColor"],
                "secondary_color": team["altColor"],
                # "roster": [ath["athlt"]["id"] for r in roster for ath in r['athlts'] if ath["athlt"].get("id")]
            })
        
        return teams  


    def _set_team_stats(self, data: dict) -> List[dict]:
        raise NotImplementedError


    

    
    


    
    

    