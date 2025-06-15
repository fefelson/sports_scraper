from datetime import datetime, timedelta
from time import sleep
import os

from ..src.capabilities.fileable import PickleAgent
from ..src.sports.leagues import MLB
basePath = os.environ["HOME"]+"/FEFelson/leagues/nba/players/"
providers = ("yahoo", "espn")

def main():
    league = MLB()
    provider = "yahoo"
    pickledPlayers = []

    for playerFile in [basePath+fileName for fileName in os.listdir(basePath)]:
        pickledPlayers.append(PickleAgent.read(playerFile))
        

    PickleAgent.write("/home/ededub/FEFelson/leagues/nba/nba_players.pkl", pickledPlayers)
    




if __name__ == "__main__":

    main()