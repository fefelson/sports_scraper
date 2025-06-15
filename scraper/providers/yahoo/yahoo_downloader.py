from copy import deepcopy
from typing import Any, Dict
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

import json

from ...capabilities.downloadable import DownloadAgent
from ...utils.logging_manager import get_logger


######################################################################
######################################################################

logger = get_logger()

class YahooDownloadAgent(DownloadAgent):

    BASE_URL = "https://sports.yahoo.com"


    @staticmethod   
    def _fetch_url(url: str, sleepTime: int = 10, attempts: int = 3) -> Dict[str, Any]:
        """
        Recursive function to download yahoo url and isolate json
        Or write to errorFile
        """
        try:
            html = urlopen(url)
            for line in [x.decode("utf-8") for x in html.readlines()]:
                if "root.App.main" in line:
                    item = json.loads(";".join(line.split("root.App.main = ")[1].split(";")[:-1]))
                    item = item["context"]["dispatcher"]["stores"]
        
        except (URLError, HTTPError, ValueError) as e:
            logger.error(e)
            # time.sleep(sleepTime)
            YahooDownloadAgent._fetch_url(url, sleepTime, attempts)
        return item
    

    @staticmethod
    def fetch_scoreboard(leagueId: str, gameDate: str) -> dict:
        slugId = {"NBA": "nba", "NCAAB": "college-basketball", "MLB": "mlb"}[leagueId]
        schedState=""
        schedUrl = YahooDownloadAgent.BASE_URL+f"/{slugId}/scoreboard/?confId=all&schedState={schedState}&dateRange={gameDate}"       
        item = YahooDownloadAgent._fetch_url(schedUrl)
        item["provider"] = "yahoo"
        return item 


    @staticmethod
    def fetch_player(leagueId:str, playerId: str):
        slugId = {"NBA": "nba", "NCAAB": "college-basketball", "MLB": "mlb"}[leagueId]
        url = YahooDownloadAgent.BASE_URL+f"/{slugId}/players/{playerId.split('.')[-1]}/"
        data = YahooDownloadAgent._fetch_url(url)["PlayersStore"]["players"][playerId]
        data["provider"] = "yahoo"
        return data
    

    @staticmethod
    def fetch_boxscore(game: dict) -> dict:
        url = YahooDownloadAgent.BASE_URL+game["url"]
        data = YahooDownloadAgent._fetch_url(url)
        gameId = data["PageStore"]["pageData"]["entityId"]

        webData = {}
        webData["provider"] = "yahoo"
        webData["gameData"] = data["GamesStore"]["games"][gameId]
        webData["teamData"] = data["TeamsStore"]
        webData["playerData"] = data["PlayersStore"]
        webData["statsData"] = data["StatsStore"]
        return deepcopy(webData)
        


        

       

    