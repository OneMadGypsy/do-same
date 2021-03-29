import gypsy as exp
from micropython import const
from gc import collect
from utime import sleep, sleep_ms
from random import randint


class SimonGame(object):
    SIMON     = const(0)
    PLAYER    = const(1)
    DURATION  = const(525)
    
    @staticmethod
    def RGB565(c:int) -> int:
        return int.from_bytes((((((c >> 16) & 248) >> 3) << 11) | ((((c >> 8) & 252) >> 2) << 5) | ((c & 248) >> 3)).to_bytes(2, 'little'), 'big')
    
    @staticmethod   
    def PAL(i:int) -> int:
        return SimonGame.RGB565([0x00cc00, 0xcccc00, 0xcc0000, 0x0000cc, 0x00ff00, 0xffff00, 0xff0000, 0x0000ff, 0x008800, 0x888800, 0x880000, 0x000088, 0x880088, 0xff00ff][i])
    
    def __init__(self) -> None:
        collect()                                                   #clean up memory
        self.__b = bytearray(115200)                                #init buffer
        
        exp.init(self.__b)                                          #init explorer
        exp.set_audio_pin(0)                                        #set audio pin
        
        self.__fart = 200                                           #loser/wrong sound
        self.__startscreen()                                        #init start screen
    
    # Start/Play Again Screen
    def __startscreen(self) -> None:
        self.__l = 1                                                #level
        self.__d = SimonGame.DURATION                               #initial note duration
        self.__u = SimonGame.SIMON                                  #current user
        self.__t = 0                                                #tries
        self.__c = [12, 6, 10, 10, 12, 10, 12, 12, 12, 12]           #character widths
        
        #draw start screen
        exp.set_pen(SimonGame.PAL(5))
        exp.clear()
        exp.set_pen(SimonGame.PAL(2))
        exp.text('DO SAME', 10, 20, 235, 6)
        exp.set_pen(0)
        exp.text('by: OneMadGypsy                                        2021', 10, 60, 240, 1)
        exp.text('A = Easy           10', 40, 100, 240, 2)
        exp.text('B = Medium       15', 40, 120, 240, 2)
        exp.text('X = Hard           25', 40, 140, 240, 2)
        exp.text('Y = Nightmare  50', 40, 160, 240, 2)
        exp.update()
        
        dfclt = [10, 15, 5, 50]                                     #difficulties
        self.__sl = 0                                               #sequence length
        #wait for difficulty selection
        while not self.__sl:
            for n in range(4):
                if exp.is_pressed(n):
                    self.__sl = dfclt[n]
                    break
            
        self.__s = [randint(0,3) for _ in range(self.__sl)]         #sequence
        self.__gameboard()                                          #draw gameboard
        sleep(1)                                                    #pause 1 second for player to prepare
        self.__gameloop()                                           #start game
    
    # Gameboard Updater        
    def __gameboard(self, seq:int=-1, user:bool=False) -> int:
        bt, tn = -1, -1
        exp.set_pen(0)
        exp.clear()
        
        #draw squares ~ capture button presses (if avail) OR Simon ~ store button tone
        for n, d in enumerate([2093, 2249, 2637, 2794]):
            p  = ((exp.is_pressed(n) and user) or (n == seq))
            bt = n if p else bt
            tn = d if p else tn
            x, y = (n>1)*120, (n%2)*120
            exp.set_pen(SimonGame.PAL(n+8))
            exp.rectangle(x+2, y+2, 116, 116)
            exp.set_pen(SimonGame.PAL(n+(4*p)))
            exp.rectangle(x+7, y+7, 106, 106)
        
        #center circle for level display
        exp.set_pen(0)
        exp.circle(120, 120, 40)  
        exp.set_pen(SimonGame.PAL(12))
        exp.circle(120, 120, 36)         
        exp.set_pen(SimonGame.PAL(13))
        exp.circle(120, 120, 31)        
        exp.set_pen(65535)
        
        #find x for center placement of level display
        if self.__l < 10:
            c = self.__c[self.__l]
        else:
            a = self.__l//10
            b = self.__l - int(a*10)
            c = self.__c[a]+self.__c[b]
            
        #display level number
        exp.text("{}".format(self.__l), 121-c, 108, 160, 4)
        exp.update()
            
        return bt, tn
    
    # Simon's Tone Player    
    def __playtone(self, tone:int, ms:int=500) -> None:
        exp.set_tone(tone)
        sleep_ms(ms)
        exp.set_tone(-1)
     
    # Gameplay Logic
    def __gameloop(self):
        while self.__l <= self.__sl:
            #adjust not duration by level
            self.__d = max(150, SimonGame.DURATION - (self.__l * self.__sl))
            #reset sequence position
            pos      = 0
            
            #Simon
            while not self.__u:
                #play sequence
                for s in range(self.__l):
                    b, t = self.__gameboard(self.__s[s])
                    self.__playtone(t, self.__d)
                #switch user
                self.__u = SimonGame.PLAYER
            
            #Player
            while self.__u:
                #update gameboard
                b, t = self.__gameboard(user=True)
                #if a button was pressed
                if b > -1:
                    #if the button matches the current sequence value
                    if b == self.__s[pos]:
                        #play tone til user releases the button
                        exp.set_tone(t) if t > -1 else None
                        while (b > -1) and exp.is_pressed(b):
                            pass   
                        exp.set_tone(-1)
                        self.__gameboard()
                        
                        #increment sequence position
                        pos += 1
                        
                        #if the spot matches the current level, increment the level and switch users
                        if pos == self.__l:
                            self.__l += 1
                            self.__u = SimonGame.SIMON
                            sleep_ms(500)
                    #if the button didn't match the current sequence value
                    else:
                        #play fart sound and increment try counter
                        self.__playtone(self.__fart, 1000)
                        self.__t += 1
                        #if all 3 tries are used up show loser message, play fart sound more and break master while condition
                        if self.__t == 3:
                            exp.text('You Lose!', 16, 30, 240, 5)
                            exp.update()
                            self.__playtone(self.__fart-100, 1000)
                            self.__l = self.__sl+2
                        #switch users ~ doesn't do anything if you lost
                        self.__u = SimonGame.SIMON
        
        #if the game has been won                
        if self.__l == (self.__sl+1):
            self.__l -= 1   #adjust for display
            #play winner animation
            for s in [0,1,2,3,0,1,2,3,0,1,2,3,0,1,2,3]:
                self.__gameboard(s)
                exp.set_pen(65535)
                exp.text('You Win!', 10, 30, 240, 6)
                exp.update()
                self.__playtone(t, 100)
        
        #go to start screen
        self.__startscreen()
                    

if __name__ == '__main__':
    SimonGame()
