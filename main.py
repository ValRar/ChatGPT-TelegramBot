import openai
import os
from os.path import join, dirname
import dotenv
import telebot
from traceback import print_exc

dotenv_path = join(dirname(__file__), '.env')
dotenv.load_dotenv(dotenv_path)
openai.api_key = os.getenv("OPENAI_KEY")
HISTORY_LIMIT = 4000

class Client(object):
    isSettingTemperature = False
    temperature = 1
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
    def setTemperature(self, temperature):
            self.temperature = temperature

class ChatGptClient(object):
    model = ""
    def __init__(self, model) -> None:
        self.model = model
    def sendPrompt(self, message, history, temperature):
        if history == None:
            history = [{"role":"user", "content": message}]
        if len(str(history)) >= HISTORY_LIMIT:
            history = [{"role":"user", "content": message}]
        completion = openai.ChatCompletion.create(
            model=self.model,
            messages=history,
            temperature=temperature
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
    bot.send_message(chat_id=message.chat.id, text="Это бот, который будет транслировать ответы ChatGPT на ваши сообщения.")

@bot.message_handler(commands=['deletecontext'])
def deleteContext(message):
    global userList
    if userList:
        index = findClient(message.chat.id)
        if index != -1:
            if userList[index].getHistory():
                userList[index].deleteHistory()
                bot.send_message(chat_id=message.chat.id, text="📃Контекст переписки успешно удалён.")
            else:
                bot.send_message(chat_id=message.chat.id, text="У вас нет истории запросов на данный момент.")
    else:
        bot.send_message(chat_id=message.chat.id, text="У вас нет истории запросов на данный момент.")

@bot.message_handler(commands=['temperature'])
def temperature(message):
    global userList
    if userList:
        index = findClient(message.chat.id)
        if index == -1:
            userList.append(Client(chatId=message.chat.id))
    else:
        userList = [Client(chatId=message.chat.id)]
        index = 0
    userList[index].isSettingTemperature = True
    temperature = userList[index].temperature
    if temperature:
        bot.send_message(chat_id=message.chat.id, text=str.format("Текущая температура ответов - {}. Введите значение от 0 до 2:", str(temperature)))
    else:
        bot.send_message(chat_id=message.chat.id, text="Текущая температура ответов - 1. Введите значение от 0 до 2:")


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
    if userList[index].isSettingTemperature == True:
        try:
            temperature = float(message.text)
        except ValueError:
            return bot.send_message(chat_id=message.chat.id, text="❌Введите корректное значение (Число от 0 до 2):")
        if temperature >= 0 and temperature <= 2:
            userList[index].setTemperature(temperature)
            userList[index].isSettingTemperature = False
            return bot.send_message(chat_id=message.chat.id, text="🌡️Температура успешно установлена на " + str(temperature))
        else:
            return bot.send_message(chat_id=message.chat.id, text="❌Введите корректное значение (Число от 0 до 2):")
    history = userList[index].getHistory()
    userList[index].addToHistory(role="user", message=message.text)
    waitMessage = bot.send_message(chat_id=message.chat.id, text="Генерация ответа... 💭")
    bot.send_chat_action(chat_id=message.chat.id, action="typing")
    try:
        answer = chatGpt.sendPrompt(message=message.text, history=history, temperature=userList[index].temperature)
        splitted_answer = telebot.util.split_string(answer, 3000)
        for answerMessage in splitted_answer:
            bot.send_message(chat_id=waitMessage.chat.id, text=answerMessage)
        userList[index].addToHistory(role="assistant", message=answer)
    except Exception as err:
        bot.send_message(chat_id=waitMessage.chat.id, text="Произошла ошибка во время генерации ответа.😭😭😭")
        print("======================================================================")
        print_exc(err)
    if len(str(userList[index].getHistory())) >= HISTORY_LIMIT:
        bot.send_message(chat_id=message.chat.id, text="📃Контекст был удалён из-за слишком большого размера.")
        userList[index].deleteHistory()

bot.infinity_polling()
# gpt-3.5-turbo