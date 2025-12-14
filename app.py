from flask import Flask, request, jsonify
from linebot.v3.messaging import (
    Configuration, ApiClient, MessagingApi,
    PushMessageRequest, TextMessage
)
from linebot.v3.webhook import WebhookHandler
from linebot.v3.webhooks import MessageEvent, TextMessageContent
from linebot.v3.messaging import ReplyMessageRequest
from linebot.v3.exceptions import InvalidSignatureError
import os

app = Flask(__name__)

# 從環境變數讀取
CHANNEL_SECRET = os.getenv('CHANNEL_SECRET')
CHANNEL_ACCESS_TOKEN = os.getenv('CHANNEL_ACCESS_TOKEN')
USER_ID = os.getenv('USER_ID')

handler = WebhookHandler(CHANNEL_SECRET)
configuration = Configuration(access_token=CHANNEL_ACCESS_TOKEN)

@app.route("/")
def home():
    return "LINE Bot 運行中！"

@app.route("/callback", methods=['POST'])
def callback():
    """LINE webhook - 接收用戶訊息"""
    signature = request.headers.get('X-Line-Signature', '')
    body = request.get_data(as_text=True)
    
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        return 'Invalid signature', 400
    
    return 'OK'

@handler.add(MessageEvent, message=TextMessageContent)
def handle_message(event):
    """回覆用戶訊息"""
    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)
        line_bot_api.reply_message(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[TextMessage(text='Bot 已收到你的訊息')]
            )
        )

@app.route("/alert", methods=['POST'])
def alert():
    """接收摔倒警報並推播給家人"""
    try:
        data = request.json
        confidence = data.get('confidence', 0)
        timestamp = data.get('timestamp', '')
        
        # 發送 LINE 推播
        with ApiClient(configuration) as api_client:
            line_bot_api = MessagingApi(api_client)
            line_bot_api.push_message(
                PushMessageRequest(
                    to=USER_ID,
                    messages=[TextMessage(
                        text=f'⚠️ 緊急警報！\n偵測到摔倒事件\n信心度: {confidence}%\n時間: {timestamp}'
                    )]
                )
            )
        
        return jsonify({"status": "success"}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', 5000)))
