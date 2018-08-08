# 這是一隻賺價差的機器人 簡易版
# 賠錢不關我的事哦〜
# 投資一定有風險，機器人操作有賺有賠，開始前應詳閱程式碼說明書。
# by https://github.com/EienYuki

import time
import datetime
import requests
from bunch import Bunch

class env_cobinhood():
	def __init__(self):
		self.root = 'https://api.cobinhood.com'
		self.timeframe = '1h'
		self.symbol = 'ETH-USDT'
		self.key = ''

	def format_value(self, obj):
		for key in obj:
			if key == 'price':
				obj[key] = float(obj[key])
			elif key == 'size':
				obj[key] = float(obj[key])
			elif key == 'filled':
				obj[key] = float(obj[key])
			elif key == 'last_trade_price':
				obj[key] = float(obj[key])
			elif key == '24h_high':
				obj[key] = float(obj[key])
			elif key == '24h_low':
				obj[key] = float(obj[key])
			elif key == '24h_open':
				obj[key] = float(obj[key])
			elif key == '24h_volume':
				obj[key] = float(obj[key])
			elif key == 'total':
				obj[key] = float(obj[key])
			elif key == 'on_order':
				obj[key] = float(obj[key])
			elif key == 'usd_value':
				obj[key] = float(obj[key])
			elif key == 'btc_value':
				obj[key] = float(obj[key])

	def set_apikey(self, data):
		self.key = data

	def set_timeframe(self, timeframe):
		self.timeframe = timeframe

	def set_symbol(self, symbol):
		self.symbol = symbol

	def get_symbols(self):
		url = self.root + '/v1/market/tickers'
		resp = requests.get(url=url)
		data = resp.json()

		out = [ r['trading_pair_id'] for r in data['result']['tickers'] ]
		return out
		
	def get_orderbooks(self):
		url = self.root + "/v1/market/orderbooks/%s" % (self.symbol)
		resp = requests.get(url=url)
		data = resp.json()

		out = data['result']['orderbook']
		return out

	def get_ticker(self):
		url = self.root + "/v1/market/tickers/%s" % (self.symbol)
		resp = requests.get(url=url)
		data = resp.json()

		out = data['result']['ticker']
		self.format_value(out)
		return out

	def get_candles(self):
		url = self.root + "/v1/chart/candles/%s?timeframe=%s" % (self.symbol, self.timeframe)
		resp = requests.get(url=url)
		data = resp.json()

		out = [ [r['timestamp'], float(r['open']), float(r['high']), float(r['low']), float(r['close']), float(r['volume']) ] for r in data['result']['candles'] ]
		return out

	def get_balances(self, currency):
		url = self.root + "/v1/wallet/balances?currency=%s" % (currency)
		headers = {
			'nonce': str(int(float(time.time()) * 1000)),
			'authorization': self.key
		}
		resp = requests.get(url=url, headers=headers)
		data = resp.json()

		try:
			out = data['result']['balances'][0]
			self.format_value(out)
			return out
		except:
			return data

	def get_order(self, order_id):
		url = self.root + "/v1/trading/orders/%s" % (order_id)
		headers = {'authorization': self.key}
		resp = requests.get(url=url, headers=headers)
		data = resp.json()
		
		try:
			out = data['result']['order']
			self.format_value(out)
			return out
		except:
			return data

	def get_orders(self):
		url = self.root + "/v1/trading/order_history"
		headers = {'authorization': self.key}
		resp = requests.get(url=url, headers=headers)
		data = resp.json()

		return data['result']['orders']

	def post_order(self, type, side, size, price):
		url = self.root + "/v1/trading/orders"
		headers = {
			'nonce': str(int(float(time.time()) * 1000)),
			'authorization': self.key
		}
		payload = {
			'trading_pair_id': self.symbol,
			'side': side,
			'type': type,
			'price': str(price),
			'size': str(size)
		}
		resp = requests.post(url=url, headers=headers, json=payload)
		data = resp.json()

		try:
			out = data['result']['order']
			self.format_value(out)
			return out
		except:
			return data

	def del_order(self, order_id):
		url = self.root + "/v1/trading/orders/" + order_id
		headers = {
			'nonce': str(int(float(time.time()) * 1000)),
			'authorization': self.key
		}
		resp = requests.delete(url=url, headers=headers)
		data = resp.json()

		return data

class bot_spread_cobinhood():
	def __init__(self, env):
		self.env = env

		self.state = Bunch()
		self.state.step = 'sell'
		self.state.order = None

		self.conf = Bunch()

		# 設定 交易對
		self.conf.symbol = self.env.symbol

		# 進行交易的資金比例
		self.conf.investment_ratio = 0.15

		# 價差百分比
		self.conf.spread_ratio = 0.5

		# 停損買
		self.conf.stop_loss_bid = 6800

		# 停損賣
		self.conf.stop_loss_ask = 6300

		# 判斷趨勢參數1 上界
		self.conf.trend_x1_max = 0.2

		# 判斷趨勢參數1 下界
		self.conf.trend_x1_min = -0.2

		# 判斷趨勢參數2 上界
		self.conf.trend_x2_max = 0.2

		# 判斷趨勢參數2 下界
		self.conf.trend_x2_min = -0.2

	def update_order(self):
		time.sleep(1)
		self.state.order = self.env.get_order(self.state.order['id'])


		if self.state.order['state'] is 'filled':
			self.state.step = 'buy' if self.state.order['side'] is 'bid' else 'sell'

	def get_trend(self, size, price, candles):
		e1 = 0
		e2 = 0
		for r in candles[ len(candles) - size: ]:
			e1 += r[1] - r[4]
			e2 += (r[2] - r[3])

		return (e1/price, e2/price)

	def buy_market(self, price):
		time.sleep(1)
		virtual, legal = self.conf.symbol.split('-')
		size = (self.env.get_balances(legal)['total'] * self.conf.investment_ratio) / price
		print('buy_market', price, size)
		
		tmp = self.env.post_order(type='market', side='bid', size=size, price=price)
		if 'error' in tmp:
			print(tmp['error'])
		else:
			self.state.order = tmp
			print(self.state.order)
			self.state.step = 'buy'

	def sell_market(self, price):
		time.sleep(1)
		print('sell_market', price, self.state.order['size'])

		tmp = self.env.post_order(type='market', side='ask', size=self.state.order['size'], price=price)
		if 'error' in tmp:
			print(tmp['error'])
		else:
			self.state.order = tmp
			print(self.state.order)
			self.state.step = 'sell'

	def buy_limit(self, price):
		time.sleep(1)
		virtual, legal = self.conf.symbol.split('-')
		size = (self.env.get_balances(legal)['total'] * self.conf.investment_ratio) / price
		print('buy_limit', price, size)

		tmp = self.env.post_order(type='limit', side='bid', size=size, price=price)
		if 'error' in tmp:
			print(tmp['error'])
		else:
			self.state.order = tmp
			print(self.state.order)
			self.state.step = 'buy_running'

	def sell_limit(self, price):
		time.sleep(1)
		print('sell_limit', price, self.state.order['size'])

		tmp = self.env.post_order(type='limit', side='ask', size=self.state.order['size'], price=price)
		if 'error' in tmp:
			print(tmp['error'])
		else:
			self.state.order = tmp
			print(self.state.order)
			self.state.step = 'sell_running'

	def run(self):
		while True:
			ticker = self.env.get_ticker()
			candles = self.env.get_candles()

			p = ticker['last_trade_price']
			e1, e2 = self.get_trend(12, p, candles)

			# 如果訂單未完成就執行更新 取得新資訊
			if self.state.step.find('running') > -1:
				self.update_order()

			if p > self.conf.stop_loss_bid:
				# 停損 買
				if not self.state.step is 'buy':
					self.buy_market(p)

			elif p < self.conf.stop_loss_ask:
				# 停損 賣
				if not self.state.step is 'sell':
					self.sell_market(p)

			elif e1 > self.conf.trend_x1_max and e2 > self.conf.trend_x2_max:
				# 上漲 狀態
				if self.state.step is 'buy':
					self.sell_limit( self.state.order['price'] * (1 + self.conf.spread_ratio) )
				elif self.state.step is 'sell':
					self.buy_limit( p * (1 - self.conf.spread_ratio) )

			elif e1 < self.conf.trend_x1_min and e2 < self.conf.trend_x2_min:
				# 下跌 狀態
				if self.state.step is 'buy':
					self.sell_limit( self.state.order['price'] * (1 + self.conf.spread_ratio) )
				elif self.state.step is 'sell':
					self.buy_limit( p * (1 - self.conf.spread_ratio) )

			else:
				# 盤整 狀態
				if self.state.step is 'buy':
					self.sell_limit( self.state.order['price'] * (1 + self.conf.spread_ratio) )
				elif self.state.step is 'sell':
					self.buy_limit( p * (1 - self.conf.spread_ratio) )

			print("%s\t e1: %.5f\t e2: %.5f\t p: %.5f\t run_state: %s [price=%.5f size=%.5f]" % (
				datetime.datetime.fromtimestamp(ticker['timestamp']/1000).strftime('%Y-%m-%d %H:%M:%S'),
				e1,
				e2,
				p,
				self.state.step,
				self.state.order['price'] if 'price' in self.state.order else 'N/A',
				self.state.order['size'] if 'size' in self.state.order else 'N/A'
			))
			time.sleep(2)

if __name__ == '__main__':
	e = env_cobinhood()
	e.set_timeframe('1h')
	e.set_symbol('BTC-USDT')
	e.set_apikey("Your API KEY")

	r = bot_spread_cobinhood(env=e)
	r.run()