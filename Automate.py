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

# locate board
winPos=pag.locateOnScreen('TopLeft.png')[:2]
boardPos=(winPos[0]+12,winPos[1]+74)
bombN=(winPos[0]+18,winPos[1]+36)

segments=(
	(5, 1),
	(1, 5),
	(9, 5),
	(5, 10),
	(1, 14),
	(10, 14),
	(5, 19)
)

# 0000
# 1  2 
# 3333 
# 4  5
# 6666
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
def readSegment(x,y,screen):
	states=[]
	for xO,yO in segments:
		wX,wY=xO+x,yO+y
		states+=[int(screen.getpixel((wX,wY)) == (255,0,0))]
	return digits[tuple(states)]

cell=lambda x,y: (boardPos[0]+x*16,boardPos[1]+y*16)
cellMid=lambda x,y: ( (boardPos[0]+x*16)+8 , (boardPos[1]+y*16)+8 )

# get board dimensions
screenshot=pag.screenshot()
boardSize=[0,0]
while True:
	try:
		possibility=screenshot.getpixel( cell(boardSize[0]+1,0) )
	except IndexError: break

	if possibility==(255, 255, 255) or possibility==(128, 128, 128): boardSize[0]+=1
	else: break

while True:
	try: 
		possibility=screenshot.getpixel( cell(0,boardSize[1]+1) )
	except IndexError: break

	if possibility==(255, 255, 255) or possibility==(128, 128, 128): boardSize[1]+=1
	else: break

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

# solving loop
colorStr=lambda r,g,b: f"\033[48;2;{r};{g};{b}m  \033[0m "

showCProc=False

while True:
	screenshot=pag.screenshot()
	bombs=readSegment(bombN[0],bombN[1],screenshot)*100
	bombs+=readSegment(bombN[0]+13,bombN[1],screenshot)*10
	bombs+=readSegment(bombN[0]+26,bombN[1],screenshot)

	grid=[[None for _ in range(boardSize[0])] for _ in range(boardSize[1])]

	try:
		for y in range(boardSize[1]):
			for x in range(boardSize[0]):
				pCell=cellMid(x,y) #cell pixel position

				#red pixel means lost game
				if screenshot.getpixel(( (boardPos[0]+x*16)+1 , (boardPos[1]+y*16)+1 ))==(255,0,0): 
					pag.click( # click on the dead face to restart game
						pag.locateOnScreen("Dead.png")
					)
					print(colorStr(164,0,0)+"Lost!")
					raise StopIteration

				# differentiate between the 2 empty cells
				if (cellCol:=screenshot.getpixel(pCell)) == (192,192,192):
					if screenshot.getpixel(cell(x,y)) == (255,255,255):
						cType="Hidden"
					else:
						cType="Solved"
				else:
					cType=numCols[cellCol] #number cells

				showCProc and print(pCell,colorStr(*cellCol),f"cell({x},{y})",cType)
				grid[y][x]=cType
	except StopIteration:
		continue

	# If no more hidden tiles, game won
	if not True in ["Hidden" in row for row in grid]:
		pag.click( #click icon to restart game
			pag.locateOnScreen("Won.png")
		)
		print(colorStr(0,255,20)+"Won!")
		continue

	sides=((1,0),(0,1),(-1,0),(0,-1),(1,1),(-1,-1),(1,-1),(-1,1))

	smthHappened=False

	for y in range(boardSize[1]):
		for x in range(boardSize[0]):
			cType=grid[y][x] # cell type
			if type(cType)==int:
				sideHidden=[]
				sideFlags=[]
				for oX,oY in sides: # cache cells beside current cell
					if (y+oY)>=boardSize[1] or (x+oX)>=boardSize[0] or 0>(x+oX) or 0>(y+oY):
						continue
					if (cCellType:=grid[y+oY][x+oX])=="Hidden":
						sideHidden+=[(x+oX,y+oY)]
					elif cCellType=="Flag":
						sideFlags+=[(x+oX,y+oY)]

				if (len(sideHidden)==cType and len(sideFlags)==0)\
				    or (len(sideHidden)+len(sideFlags))==cType:
					for bomb in sideHidden:
						pag.click(cellMid(*bomb),button="right")
						grid[bomb[1]][bomb[0]]="Flag"
						smthHappened=True
						print(colorStr(0,255,255)+f"By law of collection, {bomb} is a bomb")
				elif len(sideFlags)==cType:
					for bomb in sideHidden:
						pag.click(cellMid(*bomb),button="left")
						grid[bomb[1]][bomb[0]]="Solved"
						smthHappened=True
						print(colorStr(0,255,255)+f"By law of elimination, {bomb} is not a bomb!")

	if not smthHappened:
		print(colorStr(206,92,0)+"By law of RNG, i have to randomise.")
		possibilities=[]
		hiddenN=sum(map(lambda row: row.count("Hidden"),grid))

		# click the cell with the least chance of being a bomb
		for y in range(boardSize[1]):
			for x in range(boardSize[0]):
				if grid[y][x]=="Hidden":
					confidence=0
					chance=bombs/hiddenN
					for oX,oY in sides:
						if (cY:=y+oY)>=boardSize[1] or (cX:=x+oX)>=boardSize[0] or 0>cX or 0>cY \
						    or type(grid[cY][cX])!=int:
							continue

						sidebombs=0
						empty=0
						for iX,iY in sides:
							if (tY:=iY+cY)>=boardSize[1] or (tX:=iX+cX)>=boardSize[0] or 0>tX or 0>tY:
								continue
							if grid[tY][tX]=="Flag":
								sidebombs+=1
							elif grid[tY][tX]=="Hidden":
								empty+=1

						thisChance=(grid[cY][cX]-sidebombs)/empty
						chance=(chance+thisChance)/2

					possibilities+=[[x,y,chance]]

		possibilities=sorted(
			possibilities,
			key=lambda candidate: candidate[2]
		)

		primeChance=possibilities[0][2]
		for index,possibility in enumerate(possibilities):
			if possibility[2]>primeChance:
				possibilities=possibilities[:index]
				break

		chosen=choice(possibilities)

		fraction=Fraction(chosen[2]).limit_denominator(1000000)
		print(
			colorStr(206,92,0)+
			f"By law of probabilities, cell{chosen[:2]} of chance "
			f"{fraction.numerator}/{fraction.denominator} is chosen!"
		)

		pag.click(cellMid(
			*chosen[:2]
		))