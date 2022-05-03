import pyautogui as pag
pag.PAUSE=0.02
from time import sleep
from random import choice
from PIL import ImageGrab
from fractions import Fraction

width, height = pag.size()
def fastScreenshot():
	im = ImageGrab.grab((0, 0, width, height))
	return im

pag.screenshot=fastScreenshot

colorStr=lambda r,g,b: f"\033[48;2;{r};{g};{b}m  \033[0m "

class Board:
	def __init__(self,screenshot,winPos=None):
		if not winPos:
			self.pCornerPos=pag.locateOnScreen('Corner.png')[:2]
			self.winPos=(self.pCornerPos[0],self.pCornerPos[1]-22)
		else:
			self.winPos=winPos # start of the content, below the [x] buttons
		self.boardPos=(self.winPos[0]+12,self.winPos[1]+74) #top left of playfield
		self.bombNpos=(self.winPos[0]+18,self.winPos[1]+36) #top left of bomb counter

		self.refreshBoardSize(screenshot)

		self.timePos=(
			self.boardPos[0]+self.boardWidth-65,self.boardPos[1]-38
		) #top left of time counter
		pag.moveTo(*self.timePos)

		self.refreshBoardState(screenshot)

	def cell(self,x,y,offset=0): #macro to calculate coordinates of a cell
		return ((self.boardPos[0]+x*16)+offset,(self.boardPos[1]+y*16)+offset)

	def cellMid(self,x,y): #macro to calculate coordinates of middle of a cell
		return self.cell(x,y,offset=8)

	def withinBoard(self,x,y):
		return x>=0 and y>=0 and y<self.boardSize[1] and x<self.boardSize[0]

	def refreshBoardSize(self,screenshot): 
		# get board dimensions
		self.boardSize=[0,0]
		while True: # keep going left till pixel of suspected cell isnt valid color
			try:
				cellTopLeft=screenshot.getpixel( self.cell(self.boardSize[0]+1,0) )
			except IndexError: break # attempted cell fetch is out of screen

			if cellTopLeft==(255, 255, 255) or cellTopLeft==(128, 128, 128): self.boardSize[0]+=1
			else: break

		while True:
			try: 
				cellTopLeft=screenshot.getpixel( self.cell(0,self.boardSize[1]+1) )
			except IndexError: break

			if cellTopLeft==(255, 255, 255) or cellTopLeft==(128, 128, 128): self.boardSize[1]+=1
			else: break

		self.boardWidth=(self.boardSize[0]*16)+20

	#7-segment character parser
	segments=(
		(5, 1),
		(1, 5),
		(9, 5),
		(5, 10),
		(1, 14),
		(10, 14),
		(5, 19)
	)

	digits = {
		(1,1,1,0,1,1,1): 0,
		(0,0,1,0,0,1,0): 1,
		(1,0,1,1,1,0,1): 2,
		(1,0,1,1,0,1,1): 3,
		(0,1,1,1,0,1,0): 4,
		(1,1,0,1,0,1,1): 5,
		(1,1,0,1,1,1,1): 6,
		(1,0,1,0,0,1,0): 7,
		(1,1,1,1,1,1,1): 8,
		(1,1,1,1,0,1,1): 9,
	}

	def readSegment(self,x,y,screenshot):
		states=[]
		for xO,yO in self.segments:
			wX,wY=xO+x,yO+y
			states+=[int(screenshot.getpixel((wX,wY)) == (255,0,0))]
		return self.digits[tuple(states)]

	def readNum(self,x,y,screenshot):
		result=self.readSegment(x,y,screenshot)*100
		result+=self.readSegment(x+13,y,screenshot)*10
		result+=self.readSegment(x+26,y,screenshot)
		return result

	def refreshBombs(self,screenshot):
		self.bombs=self.readNum(*self.bombNpos,screenshot)

	def refreshTime(self,screenshot):
		self.time=self.readNum(*self.timePos,screenshot)

	# lookup table for cell colours
	numCols={
		(0,0,0): "Flag",
		(0,0,255): 1,
		(0,128,0): 2,
		(255,0,0): 3,
		(0,0,128): 4,
		(128,0,0): 5,
		(0,128,128): 6,
		(255,255,255): 7,
		(128,128,128): 8
	}
	def refreshCells(self,screenshot): #also refreshes status
		self.state="Playing"
		self.board=[[None for _ in range(self.boardSize[0])] for _ in range(self.boardSize[1])]
		for y in range(self.boardSize[1]):
			for x in range(self.boardSize[0]):
				#red pixel means lost game
				if screenshot.getpixel(self.cell(x,y,offset=1))==(255,0,0): 
					self.state="Lost"
					cType="LostMine"
				elif screenshot.getpixel(self.cell(x,y,offset=6))==(255,255,255):
					cType="Mine" #its a mine that shows after game finishes
				else:
					topLeft=screenshot.getpixel(self.cellMid(x,y))
					if topLeft == (192,192,192): # Empty cells
						if screenshot.getpixel(self.cell(x,y)) == (255,255,255): # 2 types of empty 
							cType="Hidden"
						else: 
							cType="Solved"
					else: # cells with features
						cType=self.numCols[topLeft] #number cells

				self.board[y][x]=cType

		# check for hidden tiles
		if self.state!="Lost" and (True not in map(lambda row: "Hidden" in row,self.board)):
			self.state="Won"

	def refreshBaseChance(self):
		hiddenCells=sum(map(lambda row: row.count("Hidden"),self.board))
		if hiddenCells==0:
			self.baseChance=0
		else:
			self.baseChance=self.bombs/sum(map(lambda row: row.count("Hidden"),self.board))

	def refreshBoardState(self,screenshot):
		self.refreshBombs(screenshot)
		self.refreshTime(screenshot)
		self.refreshCells(screenshot)
		self.refreshBaseChance()

	sideOffsets=((1,0),(0,1),(-1,0),(0,-1),(1,1),(-1,-1),(1,-1),(-1,1))
	def neighbourIter(self,x,y):
		for oX,oY in self.sideOffsets:
			nX,nY=x+oX,y+oY
			if self.withinBoard(nX,nY):
				yield (nX,nY,self.board[nY][nX])

	def tileIter(self,variant):
		for y in range(self.boardSize[1]):
			for x in range(self.boardSize[0]):
				if type((cell:=self.board[y][x]))==variant:
					yield (cell,x,y)

	def typeIter(self,variant):
		for y in range(self.boardSize[1]):
			for x in range(self.boardSize[0]):
				if (cell:=self.board[y][x])==variant:
					yield (cell,x,y)

	def sides(self,x,y): #get hidden cells beside, and flagged cells
		sideHidden=[]
		sideFlagN=0
		for nX,nY,cellType in self.neighbourIter(x,y):
			if cellType=="Hidden":
				sideHidden+=[(nX,nY)]
			elif cellType=="Flag":
				sideFlagN+=1
		return (sideHidden,sideFlagN)

	def flagCell(self,x,y):
		if not self.board[y][x]=="Flag":
			pag.click(self.cellMid(x,y),button="right")
			self.board[y][x]="Flag"

	def unflagCell(self,x,y):
		if not self.board[y][x]=="Flag":
			pag.click(self.cellMid(x,y),button="right")
			pag.click(self.cellMid(x,y),button="right")
			self.board[y][x]="Hidden"

	def exposeCell(self,x,y,certain=False):
		if self.board[y][x]=="Hidden":
			pag.click(self.cellMid(x,y),button="left")
			if certain:
				self.board[y][x]="Solved"

	def newGame(self):
		pag.click(self.winPos[0]+(self.boardWidth/2),self.winPos[1]+45)
		screenshot=pag.screenshot()
		self.refreshBoardState(screenshot)
		return screenshot

	# Get most likely tile to escape rng deadlock
	def probability(self,x,y):
		chance=self.baseChance
		for nX,nY,sideCell in self.neighbourIter(x,y):
			if type(sideCell)!=int:
				continue

			sidebombs=0
			empty=0
			for nnX,nnY,sideCellSide in self.neighbourIter(nX,nY):
				if sideCellSide=="Flag":
					sidebombs+=1
				elif sideCellSide=="Hidden":
					empty+=1

			thisChance=(sideCell-sidebombs)/empty
			if thisChance>chance:
				chance=(sideCell-sidebombs)/empty

		return chance

	# get cells least likely to have bombs
	def getBestCandidates(self):
		possibilities=[]
		for y in range(self.boardSize[1]):
			for x in range(self.boardSize[0]):
				if self.board[y][x]=="Hidden":
					possibilities+=[[x,y,self.probability(x,y)]]
		possibilities=sorted(
			possibilities,
			key=lambda item: item[2]
		)

		primeChance=possibilities[0][2]
		for index,possibility in enumerate(possibilities):
			if possibility[2]>primeChance:
				possibilities=possibilities[:index]
				break

		return possibilities

	def escapeRng(self):
		return choice(self.getBestCandidates())

	def advance(self,callback=None):
		if not self.state=="Playing":
			callback and callback("new",self.state)
			board.newGame()
			return

		smthHappened=False
		for bombsAround,x,y in self.tileIter(int):
			sideHidden,sideFlags=self.sides(x,y)

			if (len(sideHidden)==bombsAround and sideFlags==0)\
			    or (len(sideHidden)+sideFlags)==bombsAround:
				for bomb in sideHidden:
					self.flagCell(*bomb)
					smthHappened=True
					callback and callback("collection",bomb)

			elif sideFlags==bombsAround:
				for safe in sideHidden:
					self.exposeCell(*safe,certain=True)
					smthHappened=True
					callback and callback("elimination",safe)

		if not smthHappened:
			chosen=self.escapeRng()
			callback and callback("rng",chosen)
			self.exposeCell(*chosen[:2])

		self.refreshBoardState(pag.screenshot())

board=Board(pag.screenshot())

won,lost=0,0
wonT,lostT=0,0
def callback(eventType,data):
	global won,lost,wonT,lostT
	if eventType=="collection":
		print(colorStr(0,255,255)+f"By law of collection, {data} is a bomb")
	elif eventType=="elimination":
		print(colorStr(0,255,255)+f"By law of elimination, {data} is not a bomb!")
	elif eventType=="rng":
		fraction=Fraction(data[2]).limit_denominator(1000000)
		print(
			colorStr(206,92,0)+
			f"By law of probabilities, cell{data[:2]} of chance "
			f"{fraction.numerator}/{fraction.denominator} is chosen!"
		)
	elif eventType=="new":
		if data=="Won":
			print(colorStr(0,255,20)+f"Won with time {board.time}!")
			won+=1
			wonT+=board.time
		else:
			print(colorStr(128,0,0)+"Lost...")
			lost+=1
			lostT+=board.time

try:
	while True:
		board.advance(callback=callback)
except KeyboardInterrupt:
	avgWon=wonT/won if won!=0 else None
	avgLost=lostT/lost if lost!=0 else None
	print(f"\rWon {won} (agvT: {avgWon}), lost {lost} (avgT: {avgLost})")