from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals
from builtins import bytes, int, str
from cmd import Cmd
from steemmonsters.api import Api
from steemmonsters.constants import xp_level, max_level_rarity
from steemmonsters.utils import generate_key, generate_team_hash
from beem.blockchain import Blockchain
from beem.nodelist import NodeList
from beem import Steem
from beem.account import Account
from beembase import memo as BtsMemo
from beemgraphenebase.account import PrivateKey, PublicKey
import argparse
import json
import getpass
import random
import hashlib
from collections import OrderedDict
from datetime import date, datetime, timedelta
import requests
import logging
import os
from os.path import exists
from os.path import expanduser
import math
import six
from time import sleep
import urllib

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logging.basicConfig()

timeFormat = '%Y-%m-%dT%H:%M:%S.%fZ'

try:
    import colorama
    colorama.init()
except ImportError:
    colorama = None

try:
    from termcolor import colored
except ImportError:
    def colored(text, color):
        return text


def log(string, color, font="slant"):
    six.print_(colored(string, color))


def read_config_json(config_json, verbose=True):
    if not exists(config_json):
        if verbose:
            print("Could not find config json: %s" % config_json)
        sm_config = {}
    else:
        sm_config = json.loads(open(config_json).read())
    return sm_config


class SMPrompt(Cmd):
    prompt = 'sm> '
    intro = "Welcome to steemmonsters! Type ? to list commands"
    account = ""
    wallet_pass = ""
    api = Api()
    settings = api.settings()
    max_batch_size = 50
    threading = False
    wss = False
    https = True
    normal = False
    appbase = True
    config_file_name = "config.json"
    sm_config = read_config_json(config_file_name, verbose=False)
    if "wallet_password" in sm_config:
        wallet_pass = sm_config["wallet_password"]
    else:
        wallet_pass = getpass.getpass(prompt='Enter the beem wallet password.')
    nodes = NodeList()
    nodes.update_nodes()
    nodelist = nodes.get_nodes(normal=normal, appbase=appbase, wss=wss, https=https)
    stm = Steem(node=nodelist, num_retries=5, call_num_retries=3, timeout=15)
    stm.wallet.unlock(wallet_pass)
    b = Blockchain(mode='head', steem_instance=stm)
    cards = {}
    cards_by_name = {}
    for r in api.get_card_details():
        cards[r["id"]] = r
        cards_by_name[r["name"]] = r

    def do_exit(self, inp):
        print("Bye")
        return True

    def do_quit(self, inp):
        print("Bye")
        return True

    def help_exit(self):
        print('exit the application. Shorthand: x q Ctrl-D.')

    def do_set_account(self, inp):
        self.account = inp
        print("setting '{}'".format(inp))

    def help_set_account(self):
        print("changes the account name")

    def do_set_wallet_password(self, inp):
        print("wallet password stored")
        self.wallet_pass = inp

    def help_set_wallet_password(self):
        print("changes the wallet password")

    def do_reload_config(self, inp):
        if inp == "":
            inp = self.config_file_name
        else:
            self.config_file_name = inp
        self.sm_config = read_config_json(inp)

    def help_reload_config(self):
        print("Reloads the config, a new config files can be given as parameter")

    def do_show_config(self, inp):
        tx = json.dumps(self.sm_config, indent=4)
        print(tx)

    def help_show_config(self):
        print("Shows the loaded config file")

    def do_show_cards(self, inp):
        if inp == "":
            if len(self.sm_config) == 0:
                print("No config file loaded... aborting...")
                return
            cards = self.api.get_collection(self.sm_config["account"])
        else:
            cards = self.api.get_collection(inp)
        tx = json.dumps(cards, indent=4)
        print(tx)

    def help_show_cards(self):
        print("Shows the owned cards, an account name can be given as parameter")

    def do_conflict(self, inp):
        self.settings = self.api.settings()
        ranked_settings = self.settings["ranked_settings"]
        tx = json.dumps(ranked_settings, indent=4)
        print(tx)

    def help_conflict(self):
        print("Show current conflict")

    def do_team(self, inp):
        if inp not in self.sm_config["decks"]:
            account = self.sm_config["account"]
            mana_cap = self.settings["ranked_settings"]["mana_cap"]
            response = self.api.get_player_login(account)
            acc = Account(account, steem_instance=self.stm)
            wif = self.stm.wallet.getPrivateKeyForPublicKey(acc["posting"]["key_auths"][0][0])
            token = BtsMemo.decode_memo(PrivateKey(wif), response["token"]).replace('\n', '')
            response = self.api.get_player_saved_teams(account, token, mana_cap)
            decks = {}
            for r in response:
                summoner = r["summoner"]
                monsters = r["monsters"]
                monsters_list = []
                for m in monsters:
                    card_name = self.cards[m["id"]]["name"]
                    if m["gold"]:
                        card_name += ":gold"
                    monsters_list.append(card_name)
                summoner_name = self.cards[summoner["id"]]["name"]
                if summoner["gold"]:
                    summoner_name += ":gold"
                decks[r["name"]] = [summoner_name] + monsters_list
            if inp in decks:
                deck_ids = decks[inp]
            else:
                print("Could not find %s in saved decks" % inp)
                return
        else:
            deck_ids = self.sm_config["decks"][inp]            
        tx = json.dumps(deck_ids, indent=4)
        print(tx)

    def help_team(self):
        print("Shows defined team for given identifier")

    def do_ranking(self, inp):
        if inp == "":
            if len(self.sm_config) == 0:
                print("No config file loaded... aborting...")
                return
            account = self.sm_config["account"]
        else:
            account = inp
        response = self.api.get_player_details(account)
        tx = json.dumps(response, indent=4)
        print(tx)

    def help_ranking(self):
        print("Shows ranking, a account name can also be given.")

    def do_quest(self, inp):
        if inp == "":
            if len(self.sm_config) == 0:
                print("No config file loaded... aborting...")
                return
            account = self.sm_config["account"]
        else:
            account = inp
        response = self.api.get_player_quests(account)
        if isinstance(response, list) and len(response) == 1:
            response = response[0]        
        print("Current quest: %s" % response["name"])
        if response["claim_trx_id"] is None:
            print("Current quest is not completed (%d / %d)" % (response["completed_items"], response["total_items"]))
        else:
            print("Current quest is completed (%d / %d)" % (response["completed_items"], response["total_items"]))
        if (datetime.utcnow() - datetime.strptime(response["created_date"], timeFormat)).total_seconds() / 60 / 60 < 24:
            print("Please wait %.2f h" % (24 - (datetime.utcnow() - datetime.strptime(response["created_date"], timeFormat)).total_seconds() / 60 / 60))
        # tx = json.dumps(response, indent=4)
        # print(tx)

    def help_quest(self):
        print("Shows quest, a account name can also be given.")

    def do_player(self, inp):
        if inp == "":
            if len(self.sm_config) == 0:
                print("No config file loaded... aborting...")
                return
            account = self.sm_config["account"]
        else:
            account = inp
        response = self.api.get_player_details(account)
        tx = json.dumps(response, indent=4)
        print(tx)

    def help_player(self):
        print("Shows player, a account name can also be given.")

    def do_lastteam(self, inp):
        if inp == "":
            if len(self.sm_config) == 0:
                print("No config file loaded... aborting...")
                return
            account = self.sm_config["account"]
        else:
            account = inp
        mana_cap = self.settings["ranked_settings"]["mana_cap"]
        response = self.api.get_player_teams_last_used(account, mana_cap)
        if len(response) == 0:
            print("Error in loading last team...")
            return
        summoner = response["summoner"]
        monsters = response["monsters"]
        monsters_list = []
        for m in monsters:
            monsters_list.append(self.cards[m["id"]]["name"])
        deck = ", ".join([self.cards[summoner["id"]]["name"]] + monsters_list)
        print(deck)

    def help_lastteam(self):
        print("Shows quest, a account name can also be given.")

    def do_lasttopteam(self, inp):
        if inp == "":
            print("Give a number between 1 and 100")
            return
        elif int(inp) < 1 or int(inp) > 100:
            print("Give a number between 1 and 100")
            return
        leaderboard = self.api.players_leaderboard()
        account = leaderboard[int(inp) - 1]["player"]
        mana_cap = self.settings["ranked_settings"]["mana_cap"]
        response = self.api.get_player_teams_last_used(account, mana_cap)
        if len(response) == 0:
            print("Error in loading last team...")
            return
        summoner = response["summoner"]
        monsters = response["monsters"]
        monsters_list = []
        for m in monsters:
            monsters_list.append(self.cards[m["id"]]["name"])
        deck = ", ".join([self.cards[summoner["id"]]["name"]] + monsters_list)
        print(deck)

    def help_lasttopteam(self):
        print("Shows last played team from the top, a account name can also be given.")

    def do_copytopteam(self, inp):
        if inp == "":
            print("Give a number between 1 and 100")
            return
        account_number = inp.split(' ')[0]
        if int(account_number) < 1 or int(account_number) > 100:
            print("Give a number between 1 and 100")
            return
        leaderboard = self.api.players_leaderboard()
        account = leaderboard[int(account_number) - 1]["player"]
        deck_name = inp[len(account_number) + 1:]
        mana_cap = self.settings["ranked_settings"]["mana_cap"]
        response = self.api.get_player_teams_last_used(account, mana_cap)
        if len(response) == 0:
            print("Error in loading last team...")
            return
        summoner = response["summoner"]
        monsters = response["monsters"]
        team = OrderedDict({"summoner": summoner, "monsters": monsters})
        if six.PY2:
            team_enc = urllib.quote_plus(json.dumps(team))
        else:
            team_enc = urllib.parse.quote_plus(json.dumps(team))
        account = self.sm_config["account"]
        response = self.api.get_player_login(account)
        acc = Account(account, steem_instance=self.stm)
        wif = self.stm.wallet.getPrivateKeyForPublicKey(acc["posting"]["key_auths"][0][0])
        token = BtsMemo.decode_memo(PrivateKey(wif), response["token"]).replace('\n', '')
        print(self.api.player_save_team(deck_name, team_enc, account, token, mana_cap))

    def help_copytopteam(self):
        print("copytopteam <number> <deckname>")

    def do_copyteam(self, inp):
        if inp == "":
            if len(self.sm_config) == 0:
                return
        account = inp.split(' ')[0]
        deck_name = inp[len(account) + 1:]
        mana_cap = self.settings["ranked_settings"]["mana_cap"]
        response = self.api.get_player_teams_last_used(account, mana_cap)
        if len(response) == 0:
            print("Error in loading last team...")
            return
        summoner = response["summoner"]
        monsters = response["monsters"]
        team = OrderedDict({"summoner": summoner, "monsters": monsters})
        if six.PY2:
            team_enc = urllib.quote_plus(json.dumps(team))
        else:
            team_enc = urllib.parse.quote_plus(json.dumps(team))
        account = self.sm_config["account"]
        response = self.api.get_player_login(account)
        acc = Account(account, steem_instance=self.stm)
        wif = self.stm.wallet.getPrivateKeyForPublicKey(acc["posting"]["key_auths"][0][0])
        token = BtsMemo.decode_memo(PrivateKey(wif), response["token"]).replace('\n', '')
        print(self.api.player_save_team(deck_name, team_enc, account, token, mana_cap))

    def help_copyteam(self):
        print("copyteam <player> <deckname>")

    def do_addteam(self, inp):
        if inp == "":
            if len(self.sm_config) == 0:
                return
        account = self.sm_config["account"]
        acc = Account(account, steem_instance=self.stm)
        response = self.api.get_collection(acc["name"])
        mycards = {}
        for r in response["cards"]:
            if r["card_detail_id"] not in mycards:
                mycards[r["card_detail_id"]] = {"uid": r["uid"], "xp": r["xp"], "name": self.cards[r["card_detail_id"]]["name"],
                                                "edition": r["edition"], "id": r["card_detail_id"], "gold": r["gold"]}
            elif r["xp"] > mycards[r["card_detail_id"]]["xp"]:
                mycards[r["card_detail_id"]] = {"uid": r["uid"], "xp": r["xp"], "name": self.cards[r["card_detail_id"]]["name"],
                                                "edition": r["edition"], "id": r["card_detail_id"], "gold": r["gold"]}

        deck_name = inp.split(' ')[0]
        cards = inp[len(deck_name) + 1:]
        if cards[0] in ["\t", "\n"]:
            cards = cards[1:]
        mana_cap = self.settings["ranked_settings"]["mana_cap"]
        if len(cards.split(":")) > 0:
            summoner = {"id": self.cards_by_name[cards.split(":")[0]]["id"], "gold": False}
            monsters = []
            for m in cards[(len(cards.split(":")[0]) + 3):].split(","):
                monsters.append({"id": self.cards_by_name[m.lstrip().split(":")[0]]["id"], "gold": False})
        else:
            summoner = {"id": self.cards_by_name[cards.split(",")[0]]["id"], "gold": False}
            monsters = []
            for m in cards[(len(cards.split(",")[0]) + 1):].split(","):
                monsters.append({"id": self.cards_by_name[m.rstrip().lstrip()]["id"], "gold": False})

        if summoner["id"] not in mycards:
            print("%s is not in collection" % (self.cards[summoner["id"]]["name"]))
            return
        for m in monsters:
            if m["id"] not in mycards:
                print("%s is not in collection" % (self.cards[m["id"]]["name"]))
                return

        team = OrderedDict({"summoner": summoner, "monsters": monsters})
        if six.PY2:
            team_enc = urllib.quote_plus(json.dumps(team))
        else:
            team_enc = urllib.parse.quote_plus(json.dumps(team))

        response = self.api.get_player_login(account)

        wif = self.stm.wallet.getPrivateKeyForPublicKey(acc["posting"]["key_auths"][0][0])
        token = BtsMemo.decode_memo(PrivateKey(wif), response["token"]).replace('\n', '')
        print(self.api.player_save_team(deck_name, team_enc, account, token, mana_cap))

    def help_addteam(self):
        print("addteam <deckname> <cards>")

    def do_deleteteam(self, inp):
        if inp == "":
            if len(self.sm_config) == 0:
                return
        account = self.sm_config["account"]
        mana_cap = self.settings["ranked_settings"]["mana_cap"]
        response = self.api.get_player_login(account)
        acc = Account(account, steem_instance=self.stm)
        wif = self.stm.wallet.getPrivateKeyForPublicKey(acc["posting"]["key_auths"][0][0])
        token = BtsMemo.decode_memo(PrivateKey(wif), response["token"]).replace('\n', '')
        print(self.api.player_delete_team(inp, account, token, mana_cap))

    def help_deleteteam(self):
        print("deleteteam <deckname>")

    def do_savedteams(self, inp):
        if len(self.sm_config) == 0:
            print("No config file loaded... aborting...")
            return
        account = self.sm_config["account"]
        mana_cap = self.settings["ranked_settings"]["mana_cap"]
        response = self.api.get_player_login(account)
        acc = Account(account, steem_instance=self.stm)
        wif = self.stm.wallet.getPrivateKeyForPublicKey(acc["posting"]["key_auths"][0][0])
        token = BtsMemo.decode_memo(PrivateKey(wif), response["token"]).replace('\n', '')
        response = self.api.get_player_saved_teams(account, token, mana_cap)
        decks = {}
        for r in response:
            summoner = r["summoner"]
            monsters = r["monsters"]
            monsters_list = []
            for m in monsters:
                card_name = self.cards[m["id"]]["name"]
                if m["gold"]:
                    card_name += ":gold"
                monsters_list.append(card_name)
            summoner_name = self.cards[summoner["id"]]["name"]
            if summoner["gold"]:
                summoner_name += ":gold"
            decks[r["name"]] = ", ".join([summoner_name] + monsters_list)
        if inp == "":
            tx = json.dumps(decks, indent=4)
        else:
            tx = json.dumps(decks[inp], indent=4)
        print(tx)

    def help_savedteams(self):
        print("Shows saved teams.")

    def do_cancel(self, inp):
        if len(self.sm_config) == 0:
            print("No config file loaded... aborting...")
            return
        acc = Account(self.sm_config["account"], steem_instance=self.stm)
        self.stm.custom_json('sm_cancel_match', "{}", required_posting_auths=[acc["name"]])
        print("sm_cancel_match broadcasted!")
        sleep(3)

    def help_cancel(self):
        print("Broadcasts a custom_json with sm_cancel_match")

    def do_claimquest(self, inp):
        if len(self.sm_config) == 0:
            print("No config file loaded... aborting...")
            return
        acc = Account(self.sm_config["account"], steem_instance=self.stm)
        response = self.api.get_player_quests(acc["name"])
        if isinstance(response, list) and len(response) == 1:
            response = response[0]
        if response["claim_trx_id"] is not None:
            print("Current quest already claimed")
            return
        if response["completed_items"] < response["total_items"]:
            print("Current quest is not completed (%d / %d)" % (response["completed_items"], response["total_items"]))
            return
        json_dict = {"type": "quest", "quest_id": response["id"]}
        self.stm.custom_json('sm_claim_reward', json_dict, required_posting_auths=[acc["name"]])
        print("sm_claim_reward broadcasted!")
        sleep(3)

    def help_claimquest(self):
        print("Broadcasts a custom_json with sm_claim_reward")

    def do_startquest(self, inp):
        if len(self.sm_config) == 0:
            print("No config file loaded... aborting...")
            return
        acc = Account(self.sm_config["account"], steem_instance=self.stm)
        response = self.api.get_player_quests(acc["name"])
        if isinstance(response, list) and len(response) == 1:
            response = response[0]
        if response["claim_trx_id"] is None:
            print("Current quest is not completed (%d / %d)" % (response["completed_items"], response["total_items"]))
            return
        if (datetime.utcnow() - datetime.strptime(response["created_date"], timeFormat)).total_seconds() / 60 / 60 < 24:
            print("Please wait %.2fh" % (24 - (datetime.utcnow() - datetime.strptime(response["created_date"], timeFormat)).total_seconds() / 60 / 60))
            return
        json_dict = {"type": "daily"}
        self.stm.custom_json('sm_start_quest', json_dict, required_posting_auths=[acc["name"]])
        print("sm_start_quest broadcasted!")
        success = False
        cnt = 0
        while not success and cnt < 10:
            cnt += 1
            sleep(3)
            response = self.api.get_player_quests(acc["name"])
            if isinstance(response, list) and len(response) == 1:
                response = response[0]
            if (datetime.utcnow() - datetime.strptime(response["created_date"], timeFormat)).total_seconds() / 60 / 60 < 1.0:
                success = True
        quest_name = response["name"]
        for q in self.settings["quests"]:
            if q["name"] == quest_name:
                print(q["objective"])

    def help_startquest(self):
        print("Broadcasts a custom_json with sm_start_quest")

    def do_play(self, inp):
        if len(self.sm_config) == 0:
            print("No config file loaded... aborting...")
            return
        if inp == "":
            inp = "random"

        if inp != "random":
            if "decks" not in self.sm_config or inp not in self.sm_config["decks"]:
                account = self.sm_config["account"]
                mana_cap = self.settings["ranked_settings"]["mana_cap"]
                response = self.api.get_player_login(account)
                acc = Account(account, steem_instance=self.stm)
                wif = self.stm.wallet.getPrivateKeyForPublicKey(acc["posting"]["key_auths"][0][0])
                token = BtsMemo.decode_memo(PrivateKey(wif), response["token"]).replace('\n', '')
                response = self.api.get_player_saved_teams(account, token, mana_cap)
                decks = {}
                for r in response:
                    summoner = r["summoner"]
                    monsters = r["monsters"]
                    monsters_list = []
                    for m in monsters:
                        card_name = self.cards[m["id"]]["name"]
                        if m["gold"]:
                            card_name += ":gold"
                        monsters_list.append(card_name)
                    summoner_name = self.cards[summoner["id"]]["name"]
                    if summoner["gold"]:
                        summoner_name += ":gold"
                    decks[r["name"]] = [summoner_name] + monsters_list
                if inp in decks:
                    deck_ids = decks[inp]
                else:
                    print("Could not find %s in saved decks" % inp)
                    return
            else:
                deck_ids = self.sm_config["decks"][inp]
        else:
            deck_ids_list = list(self.sm_config["decks"].keys())
        statistics = {"won": 0, "battles": 0, "loosing_streak": 0,
                      "winning_streak": 0, "last_match_won": False, "last_match_lose": False}
        play_round = 0

        mana_cap = self.settings["ranked_settings"]["mana_cap"]
        ruleset = self.settings["ranked_settings"]["ruleset"]
        match_type = self.sm_config["match_type"]

        acc = Account(self.sm_config["account"], steem_instance=self.stm)

        response = self.api.get_player_details(acc["name"])
        print("%s rank: %s, rating: %d, battles: %d, "
              "wins: %d, cur. streak: %d" % (acc["name"], response["rank"], response["rating"],
                                             response["battles"], response["wins"], response["current_streak"]))

        response = self.api.get_collection(acc["name"])
        mycards = {}
        for r in response["cards"]:
            if r["card_detail_id"] not in mycards:
                mycards[r["card_detail_id"]] = {"uid": r["uid"], "xp": r["xp"], "name": self.cards[r["card_detail_id"]]["name"],
                                                "edition": r["edition"], "id": r["card_detail_id"], "gold": r["gold"]}
            elif r["xp"] > mycards[r["card_detail_id"]]["xp"]:
                mycards[r["card_detail_id"]] = {"uid": r["uid"], "xp": r["xp"], "name": self.cards[r["card_detail_id"]]["name"],
                                                "edition": r["edition"], "id": r["card_detail_id"], "gold": r["gold"]}
        continue_playing = True
        while continue_playing and (self.sm_config["play_counter"] < 0 or play_round < self.sm_config["play_counter"]):
            if "play_inside_ranking_border" in self.sm_config and self.sm_config["play_inside_ranking_border"]:
                ranking_border = self.sm_config["ranking_border"]
                response = self.api.get_player_details(acc["name"])
                if response["rating"] < ranking_border[0] or response["rating"] > ranking_border[1]:
                    print("Stop playing, rating %d outside [%d, %d]" % (response["rating"], ranking_border[0], ranking_border[1]))
                    continue_playing = False
                    continue
            if "stop_on_loosing_streak" in self.sm_config and self.sm_config["stop_on_loosing_streak"] > 0:
                if statistics["loosing_streak"] >= self.sm_config["stop_on_loosing_streak"]:
                    print("Stop playing, did lose %d times in a row" % (statistics["loosing_streak"]))
                    continue_playing = False
                    continue
            if inp == "random":
                deck_ids = self.sm_config["decks"][deck_ids_list[random.randint(0, len(deck_ids_list) - 1)]]
                print("Random mode: play %s" % str(deck_ids))
            if play_round > 0 and "play_delay" in self.sm_config:
                if self.sm_config["play_delay"] >= 1:
                    print("waiting %d seconds" % self.sm_config["play_delay"])
                    try:
                        sleep(self.sm_config["play_delay"])
                    except KeyboardInterrupt:
                        print("Stop playing...")
                        return
            play_round += 1
            secret = generate_key(10)
            monsters = []
            summoner = None
            summoner_level = 4
            for ids in deck_ids:
                if isinstance(ids, str):
                    card_id = self.cards_by_name[ids.split(":")[0]]["id"]
                else:
                    card_id = ids

                if card_id not in mycards:
                    print("%s is not in collection" % (self.cards[card_id]["name"]))
                    return

                if summoner is None:
                    summoner = mycards[card_id]["uid"]
                    for x in xp_level:
                        if x["edition"] == mycards[card_id]["edition"] and x["rarity"] == self.cards[card_id]["rarity"]:
                            summoner_level = 0
                            for l in x["xp_level"]:
                                if mycards[card_id]["xp"] >= x["xp_level"][l]:
                                    summoner_level = l
                    summoner_level = int(math.ceil(summoner_level / max_level_rarity[self.cards[card_id]["rarity"]] * 4))
                else:
                    monsters.append(mycards[card_id]["uid"])

            deck = {"trx_id": "", "summoner": summoner, "monsters": monsters, "secret": secret}

            team_hash = generate_team_hash(deck["summoner"], deck["monsters"], deck["secret"])
            json_data = {"match_type": match_type, "mana_cap": mana_cap, "team_hash": team_hash, "summoner_level": summoner_level, "ruleset": ruleset}
            self.stm.custom_json('sm_find_match', json_data, required_posting_auths=[acc["name"]])
            print("sm_find_match broadcasted...")
            try:
                sleep(3)
            except KeyboardInterrupt:
                print("Exiting cleanly...")
                return            
            found = False
            start_block_num = None
            for h in self.b.stream(opNames=["custom_json"]):
                if start_block_num is None:
                    start_block_num = h["block_num"]
                elif (h["block_num"] - start_block_num) * 20 > 60:
                    print("Could not find transaction id %s" % (deck["trx_id"]))
                    break
                if h["id"] == 'sm_find_match':
                    if json.loads(h['json'])["team_hash"] == team_hash:
                        found = True
                        break
            deck["trx_id"] = h['trx_id']
            block_num = h["block_num"]
            print("Transaction id found (%d - %s)" % (block_num, deck["trx_id"]))
            if not found:
                self.stm.custom_json('sm_cancel_match', "{}", required_posting_auths=[acc["name"]])
                try:
                    sleep(3)
                except KeyboardInterrupt:
                    print("Exiting cleanly...")
                    return
                continue

            response = ""
            cnt2 = 0
            trx_found = False
            while not trx_found and cnt2 < 60:
                response = requests.get("https://steemmonsters.com/transactions/lookup?trx_id=%s" % deck["trx_id"])
                if str(response) != '<Response [200]>':
                    sleep(1)
                else:
                    if 'error' in response.json() and "not found" in response.json()["error"]:
                        try:
                            sleep(1)
                        except KeyboardInterrupt:
                            print("Exiting cleanly...")
                            return
                    elif 'error' in response.json():
                        trx_found = True                    
                    elif "trx_info" in response.json() and response.json()["trx_info"]["success"]:
                        trx_found = True
                    else:
                        sleep(1)
                    # elif 'error' in response.json():
                    #    print(response.json()["error"])
                cnt2 += 1
            if 'error' in response.json():
                print(response.json()["error"])
                if "The current player is already looking for a match." in response.json()["error"]:
                    self.stm.custom_json('sm_cancel_match', "{}", required_posting_auths=[acc["name"]])
                    try:
                        sleep(3)
                    except KeyboardInterrupt:
                        print("Exiting cleanly...")
                        return
                break
            else:
                print("Transaction is valid...")
            #     print(response.json())

            match_cnt = 0
            match_found = False
            while not match_found and match_cnt < 60:
                match_cnt += 1
                response = self.api.get_battle_status(deck["trx_id"])
                if "status" in response and response["status"] > 0:
                    match_found = True
                sleep(1)
                # print("open %s" % str(open_match))
                # print("Waiting %s" % str(reveal_match))
            # print("Opponents found: %s" % str(reveal_match))
            if not match_found:
                print("Timeout and no opponent found...")
                continue
            print("Opponent found...")

            json_data = deck
            self.stm.custom_json('sm_team_reveal', json_data, required_posting_auths=[acc["name"]])
            print("sm_team_reveal broadcasted and waiting for results.")
            response = ""
            try:
                sleep(1)
            except KeyboardInterrupt:
                print("Exiting cleanly...")
                return
            cnt2 = 0

            found_match = False
            while not found_match and cnt2 < 40:
                response = requests.get("https://steemmonsters.com/battle/result?id=%s" % deck["trx_id"])
                if str(response) != '<Response [200]>':
                    try:
                        sleep(2)
                    except KeyboardInterrupt:
                        print("Exiting cleanly...")
                        return                    
                elif 'Error' in response.json():
                    try:
                        sleep(2)
                    except KeyboardInterrupt:
                        print("Exiting cleanly...")
                        return                    
                else:
                    found_match = True
                cnt2 += 1
            if cnt2 == 40:
                print("Could not found opponent!")
                self.stm.custom_json('sm_cancel_match', "{}", required_posting_auths=[acc["name"]])
                sleep(3)
                continue
            winner = response.json()["winner"]
            team1_player = response.json()["player_1"]
            team2_player = response.json()["player_2"]

            battle_details = json.loads(response.json()["details"])
            team1 = [{"id": battle_details["team1"]["summoner"]["card_detail_id"], "level": battle_details["team1"]["summoner"]["level"]}]
            for m in battle_details["team1"]["monsters"]:
                team1.append({"id": m["card_detail_id"], "level": m["level"]})
            team1_player = battle_details["team1"]["player"]
            team1_str = ""
            for m in team1:
                team1_str += self.cards[m["id"]]["name"] + ':%d, ' % m["level"]
            team1_str = team1_str[:-3]

            team2 = [{"id": battle_details["team2"]["summoner"]["card_detail_id"], "level": battle_details["team2"]["summoner"]["level"]}]
            for m in battle_details["team2"]["monsters"]:
                team2.append({"id": m["card_detail_id"], "level": m["level"]})
            team2_player = battle_details["team2"]["player"]
            team2_str = ""
            for m in team2:
                team2_str += self.cards[m["id"]]["name"] + ':%d, ' % m["level"]
            team2_str = team2_str[:-3]

            if team1_player == winner:
                print("match " + colored(team1_player, "green") + " - " + colored(team2_player, "red"))
            else:
                print("match " + colored(team2_player, "green") + " - " + colored(team1_player, "red"))

            if team1_player == acc["name"]:
                print("Opponent ranking: %d" % response.json()["player_2_rating_initial"])
                print("Opponents team: %s" % team2_str)
            else:
                print("Opponent ranking: %d" % response.json()["player_1_rating_initial"])
                print("Opponents team: %s" % team1_str)

            if winner == acc["name"]:
                if statistics["last_match_won"]:
                    statistics["winning_streak"] += 1
                statistics["won"] += 1
                statistics["loosing_streak"] = 0
                statistics["last_match_won"] = True
                statistics["last_match_lose"] = False
            else:
                if statistics["last_match_lose"]:
                    statistics["loosing_streak"] += 1
                statistics["winning_streak"] = 0
                statistics["last_match_won"] = False
                statistics["last_match_lose"] = True

            statistics["battles"] += 1
            print("%d of %d matches won using %s deck" % (statistics["won"], statistics["battles"], inp))
            if acc["name"] == response.json()["player_1"]:
                print("Score %d -> %d" % (response.json()["player_1_rating_initial"], response.json()["player_1_rating_final"]))
            else:
                print("Score %d -> %d" % (response.json()["player_2_rating_initial"], response.json()["player_2_rating_final"]))
            print("--------------")

    def help_play(self):
        print("Starts playing with given deck")

    def do_stream(self, inp):
        block_num = self.b.get_current_block_num()
        match_cnt = 0
        open_match = {}
        reveal_match = {}

        while True:
            try:
                match_cnt += 1
    
                response = self.api.get_from_block(block_num)
                for r in response:
                    block_num = r["block_num"]
                    if r["type"] == "sm_find_match":
                        player = r["player"]
                        player_info = self.api.get_player_details(player)
                        if not r["success"]:
                            continue
    
                        data = json.loads(r["data"])
                        if data["match_type"] != "Ranked":
                            continue
                        if player not in open_match:
                            open_match[player] = {"type": r["type"], "block_num": block_num, "player": player, "mana_cap": data["mana_cap"], "summoner_level": data["summoner_level"]}
                            log("%s (%d) with summoner_level %d starts searching (%d player searching)" % (player, player_info["rating"], data["summoner_level"], len(open_match)), color="yellow")
                    elif r["type"] == "sm_team_reveal":
                        result = json.loads(r["result"])
                        player = r["player"]
    
                        if player in open_match:
                            player_data = open_match.pop(player)
                            waiting_time = (block_num - player_data["block_num"]) * 3
                        else:
                            waiting_time = 0
                            if "battle" in result:
                                mana_cap = result["battle"]["mana_cap"]
                            else:
                                mana_cap = 0
                            player_data = {"type": r["type"], "block_num": block_num, "player": player, "mana_cap": mana_cap, "summoner_level": 0}
                        if player not in reveal_match:
                            if "status" in result and "Waiting for opponent reveal." in result["status"]:
                                reveal_match[player] = player_data
                                log("%s waits for opponent reveal after %d s (%d player waiting)" % (player, waiting_time, len(reveal_match)), color="white")
                        else:
                            if "status" in result and "Waiting for opponent reveal." not in result["status"]:
                                reveal_match.pop(player)
    
                        if "battle" in result:
                            team1 = [{"id": result["battle"]["details"]["team1"]["summoner"]["card_detail_id"], "level": result["battle"]["details"]["team1"]["summoner"]["level"]}]
                            for m in result["battle"]["details"]["team1"]["monsters"]:
                                team1.append({"id": m["card_detail_id"], "level": m["level"]})
                            team1_player = result["battle"]["details"]["team1"]["player"]
                            team1_summoner = result["battle"]["details"]["team1"]["summoner"]
                            summoner1 = self.cards[team1_summoner["card_detail_id"]]["name"] + ':%d' % team1_summoner["level"]
    
                            team2 = [{"id": result["battle"]["details"]["team2"]["summoner"]["card_detail_id"], "level": result["battle"]["details"]["team2"]["summoner"]["level"]}]
                            for m in result["battle"]["details"]["team2"]["monsters"]:
                                team2.append({"id": m["card_detail_id"], "level": m["level"]})
                            team2_player = result["battle"]["details"]["team2"]["player"]
                            team2_summoner = result["battle"]["details"]["team2"]["summoner"]
                            summoner2 = self.cards[team2_summoner["card_detail_id"]]["name"] + ':%d' % team2_summoner["level"]
                            winner = result["battle"]["details"]["winner"]
                            if team1_player == winner:
                                print("match " + colored("%s (%s)" % (team1_player, summoner1), "green") + " - " + colored("%s (%s)" % (team2_player, summoner2), "red"))
                            else:
                                print("match " + colored("%s (%s)" % (team2_player, summoner2), "green") + " - " + colored("%s (%s)" % (team1_player, summoner1), "red"))
                            if team2_player in open_match:
                                open_match.pop(team2_player)
                            if team1_player in open_match:
                                open_match.pop(team1_player)
                            if team2_player in reveal_match:
                                reveal_match.pop(team2_player)
                            if team1_player in reveal_match:
                                reveal_match.pop(team1_player)
            except KeyboardInterrupt:
                print("Exiting cleanly...")
                return

    def help_stream(self):
        print("Shows who is currently playing.")

    def default(self, inp):
        if inp == 'x' or inp == 'q':
            return self.do_exit(inp)

        print("Default: {}".format(inp))

    do_EOF = do_exit
    help_EOF = help_exit


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--config")
    args = parser.parse_args()
    smprompt = SMPrompt()
    if args.config:
        smprompt.do_reload_config(args.config)
    smprompt.cmdloop()


if __name__ == '__main__':
    main()
