# -*- coding: utf-8 -*
from __future__ import print_function
from proxyscrape import create_collector
from lxml import html
from bs4 import BeautifulSoup
from re import sub
from decimal import Decimal
from telegram.ext import Updater, CommandHandler, run_async
import logging
import winsound
import webbrowser
import threading
import time
import requests
from time import gmtime, strftime
import random
from fake_useragent import UserAgent

import pickle
import os.path
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

from selenium import webdriver
from selenium.webdriver.chrome.options import Options

XPATH_PRODUCT_PRICE = ".//span[contains(@class, 'olpOfferPrice')]//text()"
XPATH_PRODUCT_SELLER1 = ".//h3[contains(@class, 'olpSellerName')]//a/text()"
XPATH_PRODUCT_SELLER2 = ".//h3[contains(@class, 'olpSellerName')]//img//@alt"
XPATH_PRODUCT_LISTINGS = "//div[contains(@class, 'a-row a-spacing-mini olpOffer')]"

ua = UserAgent()
chrome_path = 'C:/Program Files (x86)/Google/Chrome/Application/chrome.exe %s'

chrome_options = Options()
chrome_options.add_argument("--headless")
driver = webdriver.Chrome("D:/Adrian/Mask/venv/chromedriver",options=chrome_options)

# If modifying these scopes, delete the file token.pickle.
SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']

# The ID and range of a sample spreadsheet.
SAMPLE_SPREADSHEET_ID = ''
SAMPLE_RANGE_NAME = 'sheet1'

prodName = []
url = []
curprice = []
threshhold = []
resetTimer = []
hasSeller = []

gProxies = []

creds = None
# The file token.pickle stores the user's access and refresh tokens, and is
# created automatically when the authorization flow completes for the first
# time.
if os.path.exists('token.pickle'):
    with open('token.pickle', 'rb') as token:
        creds = pickle.load(token)
# If there are no (valid) credentials available, let the user log in.
if not creds or not creds.valid:
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    else:
        flow = InstalledAppFlow.from_client_secrets_file(
            'credentials.json', SCOPES)
        creds = flow.run_local_server(port=0)
    # Save the credentials for the next run
    with open('token.pickle', 'wb') as token:
        pickle.dump(creds, token)

service = build('sheets', 'v4', credentials=creds)

# Call the Sheets API
sheet = service.spreadsheets()

def proddetails():
    result = sheet.values().get(spreadsheetId=SAMPLE_SPREADSHEET_ID,
                                range=SAMPLE_RANGE_NAME).execute()
    values = result.get('values', [])
    del values[0]

    prodName1 = []
    url1 = []
    curprice1 = []
    threshhold1 = []
    resetTimer1 = []
    hasSeller1 = []

    for row in values:
        prodName1.append(row[0].encode('utf-8'))
        url1.append(str(row[1]))
        curprice1.append(float(row[2])+1000)
        threshhold1.append(float(row[2]))
        resetTimer1.append(0)
        hasSeller1.append(False)

    if url1 != url:
        global prodName
        global url
        global curprice
        global threshhold
        global resetTimer
        global hasSeller
        prodName = prodName1
        url = url1
        curprice = curprice1
        threshhold = threshhold1
        resetTimer = resetTimer1
        hasSeller = hasSeller1


def proxyList():
    proxies = []  # Will contain proxies [ip, port]
    headers = {'user-agent': ua.random}
    resp = requests.get("https://www.sslproxies.org/", headers=headers)
    soup = BeautifulSoup(resp.text, 'html.parser')
    proxies_table = soup.find(id='proxylisttable')
    # Save proxies in the array
    for row in proxies_table.tbody.find_all('tr'):
        proxies.append({
            'ip': row.find_all('td')[0].string,
            'port': row.find_all('td')[1].string
        })
    return proxies


prodTimer = 10
proxyTimer = 0
proxylistTimer = 0
cooldownTimer = 10
lastAttempt = strftime("%Y-%m-%d %H:%M:%S", time.localtime())

#proddetails()

if not len(url)==len(prodName)==len(curprice)==len(threshhold)==len(resetTimer):
    print("Wrong input")
    exit

token = ''
tgurl = ""

def sendmsg(text):
    params = {'chat_id': -250588088, 'text': text}
    #params = {'chat_id': -301886923, 'text': text}
    response = requests.post(tgurl + 'sendMessage', data=params)
    return response

def updating():
    global prodTimer, proxylistTimer,proxyTimer, ttcollector, ttproxy
    if prodTimer == 10:
        proddetails()
        prodTimer = 0
    else:
        prodTimer += 1

    if proxylistTimer == 10:
        #gProxies = proxyList()
        ttcollector = create_collector('my-collector', 'http')
        ttproxy = collector.get_proxy()

        proxylistTimer = 0
    else:
        proxylistTimer += 1

    lastAttempt = strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    print("Attempt: " + lastAttempt)
    idx = random.randint(0, len(gProxies) - 1)
    for i in range(len(url)):
        if (resetTimer[i] > 0):
            resetTimer[i] -= 1

        if proxyTimer == 10:
            idx = random.randint(0, len(gProxies) - 1)
            proxyTimer = 0
        else:
            proxyTimer += 1
        cip = gProxies[idx]['ip'] + ':' + gProxies[idx]['port']
        proxy = {"http": "http://" + cip, "https": "https://" + cip}
        headers = {'user-agent': ua.random}
        failurl = True
        while failurl:
            failurl = False
            try:
                resp = requests.get(url[i], headers=headers, proxies=proxy)
            except:  # If error, delete this proxy and find another one
                del gProxies[idx]
                print("try again change proxy")
                failurl = True
                idx = random.randint(0, len(gProxies) - 1)
                cip = gProxies[idx]['ip'] + ':' + gProxies[idx]['port']
                proxy = {"http": "http://" + cip, "https": "https://" + cip}

        resp = requests.get(url[i], headers=headers, proxies=proxy)
        response_text = resp.text
        parser = html.fromstring(response_text)
        listings = parser.xpath(XPATH_PRODUCT_LISTINGS)

        if not listings:
            print(prodName[i] + "  no sellers found")
            hasSeller[i] = False
        else:
            hasSeller[i] = True
            listing = listings[0]
            product_price = listing.xpath(XPATH_PRODUCT_PRICE)
            product_price = product_price[0].strip().split()[1]
            curprice[i] = Decimal(sub(r'[^\d.]', '', product_price))
            seller1 = listing.xpath(XPATH_PRODUCT_SELLER1)
            print(prodName[i] + '  Price: ' + str(curprice[i]) + ";  " + 'Threshold: ' + str(threshhold[i]))
            if curprice[i] <= threshhold[i] and resetTimer[i] == 0:
                webbrowser.get(chrome_path).open(url[i])
                sendmsg(prodName[i] + '\n現價: ' + str(curprice[i]) + ";  " + '上限: ' + str(threshhold[i]))
                sendmsg(url[i])
                #winsound.Beep(freq, duration)
                resetTimer[i] = cooldownTimer

def bgupdate():
    global gProxies
    gProxies = proxyList()
    proddetails()
    while True:
        updating()
        time.sleep(60)

t = threading.Thread(target = bgupdate)
t.start()

def start(update, context):
    context.bot.send_message(chat_id=update.effective_chat.id, text="I'm a bot, please talk to me!")

def maskinfo(update, context):
    context.bot.send_message(chat_id=update.effective_chat.id, text="Attempt: " + lastAttempt)
    outputtxt = ""
    for i in range(len(url)):
        if hasSeller[i] == True:
            outputtxt += prodName[i] + '\n現價: ' + str(curprice[i]) + ";  " + '上限: ' + str(threshhold[i]) + "\n\n\n"
        else:
            outputtxt += prodName[i] + '\n現價: NA' + ";  " + '上限: ' + str(threshhold[i]) + "\n\n\n"
    context.bot.send_message(chat_id=update.effective_chat.id, text=outputtxt)

def f5(update, context):
    proddetails()
    updating()
    maskinfo(update,context)

updater = Updater(token, use_context=True)
dispatcher = updater.dispatcher
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                     level=logging.INFO)

start_handler = CommandHandler('start', start)
dispatcher.add_handler(start_handler)
dispatcher.add_handler(CommandHandler('maskinfo', maskinfo))
dispatcher.add_handler(CommandHandler('f5', f5))

updater.start_polling()
#updater.idle()





'''
prodName = ['(PM2.5対応)快適ガードさわやかマスク レギュラーサイズ 60枚入',
            '(個別包装) フィッティ 7DAYS マスク 100枚入 ふつうサイズ ホワイト PM2.5対応',
            '(PM2.5対応) フィッティ オメガプリーツ マスク 60枚入 ふつうサイズ ホワイト',
            '[Amazon Original] Presto. (PM2.5) Comfortable Premium Mask smaller size 200 Pieces (50 Pieces x 4 Pack)',
            '(PM2.5 Support) Fitty 7days Mask EX, White, 60 Ct., , , whites',
            'Fitty Silky Touch More Mask, White, Regular Size, Pack of 50, , ,',
            'Comfortable Guard Refreshing Mask, Small Size, White']
url = ["https://www.amazon.co.jp/gp/offer-listing/B0141ZPO1E/ref=dp_olp_new_mbc?ie=UTF8&condition=new",
       "https://www.amazon.co.jp/gp/offer-listing/B0141ZPO1E/ref=dp_olp_new_mbc?ie=UTF8&condition=new",
       "https://www.amazon.co.jp/gp/offer-listing/B07573632C/ref=dp_olp_new_mbc?ie=UTF8&condition=new",
       "https://www.amazon.co.jp/gp/offer-listing/B077Z999TC/ref=dp_olp_new_mbc?ie=UTF8&condition=new",
       "https://www.amazon.co.jp/gp/offer-listing/B01HNYW39G/ref=dp_olp_new_mbc?ie=UTF8&condition=new",
       "https://www.amazon.co.jp/gp/offer-listing/B075MWTSMJ/ref=dp_olp_new_mbc?ie=UTF8&condition=new",
       "https://www.amazon.co.jp/gp/offer-listing/B0141ZPNR4/ref=dp_olp_new_mbc?ie=UTF8&condition=new"]
curprice = [100000,100000,100000,100000,100000,100000,100000]
threshhold = [2000,2000,1500,3500,1500,1000,1200]
resetTimer = [0,0,0,0,0,0,0]
'''
