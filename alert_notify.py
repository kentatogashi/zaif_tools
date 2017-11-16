import requests
import smtplib
from email.mime.text import MIMEText
import time
import os.path

class ZaifAlert(object):
    def __init__(self, pair):
        self.pair = pair
        self.url = 'https://api.zaif.jp/api/1/last_price/%s' % self.pair
        self.prev_data_file = './previous_price.txt'
        self.from_addr = 'postmaster@example.com'
        self.to_addr = 'kenta.togasi@example.com'
        self.smtp_host = 'localhost'

    def __get_last_price(self):
        res = requests.get(self.url)
        return res.json()['last_price']

    def __get_prev_price(self):
        if os.path.isfile(self.prev_data_file):
            with open(self.prev_data_file, 'r') as f:
                return float(f.read().strip())
        else:
            return 20.0

    def check(self):
        self.last_price = self.__get_last_price()
        self.prev_price = self.__get_prev_price()
        if (self.last_price // 1) != (self.prev_price // 1):
            self.__notify(self.last_price, self.prev_price)
        else:
            pass

        with open(self.prev_data_file, 'w') as f:
            f.write(str(self.last_price))

    def __notify(self):
        msg = MIMEText("%s: %s" % (self.pair, self.last_price))
        msg['Subject'] = '%s price alert' % self.pair
        msg['From'] = self.from_addr
        msg['To'] = self.to_addr
        s = smtplib.SMTP(self.smtp_host)
        s.connect()
        s.sendmail(self.from_addr, [self.to_addr], msg.as_string())
        s.close()

while True:
    pair = 'xem_jpy'
    zaif = ZaifAlert(pair)
    zaif.check()
    time.sleep(60)
