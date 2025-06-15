from typing import Any, Dict
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

import json
import re 
from time import sleep
from ...capabilities.fileable import JSONAgent
from ...capabilities.downloadable import DownloadAgent
from ...utils.logging_manager import get_logger


######################################################################
######################################################################

logger = get_logger()

class ESPNDownloadAgent(DownloadAgent):

    BASE_URL = "https://www.espn.com"


    @staticmethod   
    def _fetch_url(url: str, sleepTime: int = 10, attempts: int = 3) -> Dict[str, Any]:
        """
        Recursive function to download yahoo url and isolate json
        Or write to errorFile
        """
        try:
            html = urlopen(url)
            for line in [x.decode("utf-8") for x in html.readlines()]:
                if "window['__CONFIG__']=" in line:
                    item = json.loads("".join(line.split("window['__espnfitt__']=")[1].split(";</script>")[:-1]))
        
        except (URLError, HTTPError, ValueError) as e:
            logger.error(e)
            # time.sleep(sleepTime)
            ESPNDownloadAgent._fetch_url(url, sleepTime, attempts)
        return item
    

    @staticmethod
    def fetch_scoreboard(leagueId: str, gameDate: str) -> dict:
        slugId = {"NBA": "nba", "NCAAB": "college-basketball", "MLB": "mlb"}[leagueId]
        schedUrl = ESPNDownloadAgent.BASE_URL+f"/{slugId}/scoreboard/_/date/{''.join(gameDate.split('-'))}"       
        data = ESPNDownloadAgent._fetch_url(schedUrl)
        data["provider"] = "espn"
        return data
    

    @staticmethod
    def fetch_boxscore(game: dict) -> dict:
        
        gameUrl = ESPNDownloadAgent.BASE_URL+game["url"]
        pbpUrl = re.sub("game", "playbyplay", gameUrl, 1)
        pbp = ESPNDownloadAgent._fetch_url(pbpUrl)["page"]["content"]["gamepackage"]
        box = ESPNDownloadAgent._fetch_url(gameUrl)["page"]["content"]["gamepackage"]
        data = {"box":box, "pbp":pbp, "provider":"espn"}
        return data
        


        

       

    