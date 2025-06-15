from typing import Optional

from .espn.espn_downloader import ESPNDownloadAgent
from .espn.normalizers.espn_mlb_normalizer import ESPNMLBNormalizer
from .espn.normalizers.espn_basketball_normalizer import ESPNBasketballNormalizer
from .yahoo.yahoo_downloader import YahooDownloadAgent
from .yahoo.normalizers.yahoo_basketball_normalizer import YahooBasketballNormalizer
from .yahoo.normalizers.yahoo_mlb_normalizer import YahooMLBNormalizer



default_provider = "yahoo"


def get_normal_agent(leagueId: str, provider: Optional[str]=None) -> "NormalAgent":
    if not provider:
        provider = default_provider

    return {"yahoo": {"NBA": YahooBasketballNormalizer,
                      "NCAAB": YahooBasketballNormalizer,
                      "MLB": YahooMLBNormalizer},
            
            "espn": {"NBA": ESPNBasketballNormalizer,
                      "NCAAB": ESPNBasketballNormalizer,
                      "MLB": ESPNMLBNormalizer}
            }[provider][leagueId](leagueId)



def get_download_agent(leagueId: str, provider: Optional[str]=None) -> "DownloadAgent":
    if not provider:
        provider = default_provider
    
    return {"yahoo": {"NBA": YahooDownloadAgent,
                      "NCAAB": YahooDownloadAgent,
                      "NFL": YahooDownloadAgent,
                      "NCAAF": YahooDownloadAgent,
                      "MLB": YahooDownloadAgent},
            
            "espn": {"NBA": ESPNDownloadAgent,
                      "NCAAB": ESPNDownloadAgent,
                      "NFL": ESPNDownloadAgent,
                      "NCAAF": ESPNDownloadAgent,
                      "MLB": ESPNDownloadAgent}

            }[provider][leagueId]