# coding:utf-8
import os
import re


from flask import Flask
from slack import WebClient
from slackeventsapi import SlackEventAdapter

from botfunc import world_greeting, search_connpass_online, jma_weekly_weather


# TODO:2020-08-08 これをnamedtuple or dataclassesにするほうがいいかな？
BOT_FUNCTIONS = [
    (r"^wgreet", world_greeting),
    (r"^connpass\s(¥d{6})", search_connpass_online),
    (r"^tenki\s(.{1,4})", jma_weekly_weather),
]

# Flaskを作ってgunicornで動くようにする
app = Flask(__name__)

# Events APIの準備
slack_signing_secret = os.environ["SLACK_SIGNING_SECRET"]
slack_events_adapter = SlackEventAdapter(slack_signing_secret, "/slack/events", app)

# Web Client APIの準備
slack_bot_token = os.environ["SLACK_BOT_TOKEN"]
slack_client = WebClient(slack_bot_token)


@slack_events_adapter.on("message")
def handle_message_and_botrun(event_data):

    # TODO:2020/08/05 できればdebugはlogging.debugにしたい。
    print("debug: eventdata:{}".format(event_data))
    message = event_data["event"]

    # subtypeがない場合=普通のメッセージ, botの返答メッセージはスルーする
    if message.get("subtype") is None and message.get("bot_id") is None:

        # botが返す結果の入れ物
        bot_result = ""

        # ハンドルするワードパターンとcallするfucntionのリストをみて、
        for bot_pattern, bot_module in BOT_FUNCTIONS:
            print("debug: try matching bot:{}".format(bot_module))

            matched_obj = re.match(bot_pattern, message.get("text"))
            if not matched_obj:
                continue

            print("info: matched_obj -> bot!:{}".format(bot_module))

            # TODO:2020/08/05 ここの引数をどう入れるかを考える:引数というかグループ化した結果の文字を取りに行くだけで良いかなと
            bot_result = bot_module.call_function(matched_obj.groups()[0])

            # botが何かしら返答をしてくれた場合はその時点で終了
            if bot_result is not None:
                break

        if bot_result is not None:
            res_message = bot_result
            channel = message["channel"]
            slack_client.chat_postMessage(channel=channel, text=res_message)


# エラー時のイベントのハンドリング
@slack_events_adapter.on("error")
def error_handler(err):
    print("ERROR: " + str(err))


# botアプリを起動する:FlaskサーバーでEvent APIを待機する
if __name__ == "__main__":
    print("run slackbot")
    app.run(port=3000)
