import openai
import os
from os.path import join, dirname
import dotenv
import telebot
from time import time

dotenv_path = join(dirname(__file__), '.env')
dotenv.load_dotenv(dotenv_path)
openai.api_key = os.getenv("OPENAI_KEY")
class Client(object):
    id = ""
    chatHistory = []
    def __init__(self, chatId):
        self.id = chatId

    def addToHistory(self, role, message):
        self.chatHistory.append({"role": role, "content": message})
        if self.chatHistory == None:
            self.chatHistory = [{"role": role, "content": message}]

    def deleteHistory(self):
        self.chatHistory = []
    def getHistory(self):
        return self.chatHistory
    def getId(self):
        return self.id

class ChatGptClient(object):
    model = ""
    def __init__(self, model) -> None:
        self.model = model
    def sendPrompt(self, message, history):
        if history == None:
            history = [{"role":"user", "content": message}]
        # print(context)
        completion = openai.ChatCompletion.create(
            model=self.model,
            messages=history,
        )
        return completion.choices[0].message.content

userList = []

bot = telebot.TeleBot(token=os.getenv("TELEGRAM_KEY"))

chatGpt = ChatGptClient(model="gpt-3.5-turbo")

def findClient(id):
    for i in range(len(userList)):
        if userList[i].getId() == id:
            return i
    return -1


@bot.message_handler(commands=['start'])
def startCommand(message):
    bot.send_message(chat_id=message.chat.id, text="Это бот, который будет транслировать ответы chatgpt на ваши сообщения.")

@bot.message_handler(commands=['deletecontext'])
def deleteContext(message):
    global userList
    if userList:
        index = findClient(message.chat.id)
        if index != -1:
            userList[index].deleteHistory()
            bot.send_message(chat_id=message.chat.id, text="Контекст переписки успешно удалён.")
    else:
        bot.send_message(chat_id=message.chat.id, text="У вас нет истории запросов на данный момент.")

@bot.message_handler(func=lambda m: True)
def handleMessage(message):
    global userList
    if userList:
        index = findClient(message.chat.id)
        if index == -1:
            userList.append(Client(chatId=message.chat.id))
    else:
        userList = [Client(chatId=message.chat.id)]
        index = 0
    history = userList[index].getHistory()
    userList[index].addToHistory(role="user", message=message.text)
    waitMessage = bot.send_message(chat_id=message.chat.id, text="Генерация ответа...")
    try:
        answer = chatGpt.sendPrompt(message=message.text, history=history)
        bot.send_message(chat_id=waitMessage.chat.id, text=answer)
        userList[index].addToHistory(role="assistant", message=answer)
    except:
        bot.send_message(chat_id=waitMessage.chat.id, text="Произошла ошибка во время генерации ответа.😭😭😭")



bot.infinity_polling()
# gpt-3.5-turbo