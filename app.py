from flask import Flask, request, jsonify
from linebot.v3.messaging import (
    Configuration, ApiClient, MessagingApi,
    PushMessageRequest, TextMessage, ReplyMessageRequest
)
from linebot.v3.webhook import WebhookHandler
from linebot.v3.webhooks import MessageEvent, TextMessageContent
from linebot.v3.exceptions import InvalidSignatureError
import os

app = Flask(__name__)

CHANNEL_SECRET = os.getenv('CHANNEL_SECRET')
CHANNEL_ACCESS_TOKEN = os.getenv('CHANNEL_ACCESS_TOKEN')
ADMIN_USER_ID = 'U391bbcf8ec981740622526c3dcc260ef'  # 你的 User ID（管理員）

# 動態聯絡人清單
family_contacts = [ADMIN_USER_ID]  # 預設只有你

handler = WebhookHandler(CHANNEL_SECRET)
configuration = Configuration(access_token=CHANNEL_ACCESS_TOKEN)

@app.route("/")
def home():
    return "LINE Bot 運行中"

@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers.get('X-Line-Signature', '')
    body = request.get_data(as_text=True)
    
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        return 'Invalid signature', 400
    
    return 'OK'

@handler.add(MessageEvent, message=TextMessageContent)
def handle_message(event):
    user_id = event.source.user_id
    message = event.message.text.strip()
    
    # 只有管理員可以管理聯絡人
    if user_id != ADMIN_USER_ID:
        reply_text = f'你的 User ID:\n{user_id}\n\n請將此 ID 提供給管理員'
    else:
        # 管理員指令
        if message.startswith('新增'):
            # 格式：新增 Uxxxxxxxxxxxxx
            new_id = message.replace('新增', '').strip()
            if new_id.startswith('U') and len(new_id) == 33:
                if new_id not in family_contacts:
                    family_contacts.append(new_id)
                    reply_text = f'✅ 已新增聯絡人\n總共 {len(family_contacts)} 人'
                else:
                    reply_text = '⚠️ 此聯絡人已存在'
            else:
                reply_text = '❌ User ID 格式錯誤'
        
        elif message.startswith('刪除'):
            # 格式：刪除 Uxxxxxxxxxxxxx
            del_id = message.replace('刪除', '').strip()
            if del_id in family_contacts and del_id != ADMIN_USER_ID:
                family_contacts.remove(del_id)
                reply_text = f'✅ 已刪除聯絡人\n總共 {len(family_contacts)} 人'
            elif del_id == ADMIN_USER_ID:
                reply_text = '❌ 不能刪除管理員'
            else:
                reply_text = '❌ 找不到此聯絡人'
        
        elif message == '清單':
            contacts_list = '\n'.join([f'{i+1}. {uid}' for i, uid in enumerate(family_contacts)])
            reply_text = f'📋 聯絡人清單 ({len(family_contacts)} 人):\n\n{contacts_list}'
        
        else:
            reply_text = '''🔧 管理指令:
            
新增 User_ID - 新增聯絡人
刪除 User_ID - 刪除聯絡人  
清單 - 查看所有聯絡人

範例:
新增 U1234567890abcdef'''
    
    # 回覆
    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)
        line_bot_api.reply_message(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[TextMessage(text=reply_text)]
            )
        )

@app.route("/alert", methods=['POST'])
def alert():
    """發送警報給所有聯絡人"""
    data = request.json
    
    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)
        
        for user_id in family_contacts:
            try:
                line_bot_api.push_message(
                    PushMessageRequest(
                        to=user_id,
                        messages=[TextMessage(
                            text=f'⚠️ 緊急警報！\n偵測到摔倒事件\n時間: {data.get("timestamp")}'
                        )]
                    )
                )
            except Exception as e:
                print(f"發送失敗 {user_id}: {e}")
    
    return jsonify({"status": "success", "sent_to": len(family_contacts)}), 200

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', 5000)))
