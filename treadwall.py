#!/usr/bin/python3
# -*-coding:Utf-8 -*-

# version z-4.4 :
#restaurer  service avec info

import math
import RPi.GPIO as GPIO
from guizero import App, Text, TextBox, PushButton, Box, Picture, ListBox, Combo, Window, yesno
from subprocess import run
import os, re, time, subprocess, shutil

reed_switch_pin = 16 #GPIO 16 on board (pin #36)
GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)
# set as inputs with pull ups
GPIO.setup(reed_switch_pin, GPIO.IN, pull_up_down = GPIO.PUD_UP) 
reed_switch_state = GPIO.input(reed_switch_pin) #False #True
reed_switch_count = 0
reed_switch_count0 = 0

distance = 0
distance_scaling_factor_init = 0.5 # feet per reed switch count
distance_scaling_factor = distance_scaling_factor_init
# distance_scaling_factor * 0.3048 = meters per reed switch count

refresh_ms = 20
current_time_ms = 0
current_time_sec = 0
current_time_min = 0

idle_time_sec = 10 # will pause the timer and reset the reed count
reset_time_sec = 900 # 15 minutes or 900 seconds
idle_cycles_count = 0
idle_cycles_max = 1e9 # a large number
paused = False # paused until first reed switch reeding
reset = False # reset flag

def read_resetonoff() :
    with open("/home/treadwall/Display/resetonoff.txt","r") as f :
        read_reset = f.read()
    vresetonoff = True if read_reset== "true" else False# reset on-off flag
    return vresetonoff

def save_resetonoff(vresetonoff) :
    read_reset = "true" if vresetonoff == True else "false"
    with open("/home/treadwall/Display/resetonoff.txt","w") as f :
        f.write(read_reset)

def save_unit(vunit) :
    with open("/home/treadwall/Display/unit.txt","w") as f :
        f.write(vunit)

#total_dist_init, total_unit = total_read()
resetonoff = read_resetonoff()
speed = 0
button_text_size = 20
text_size = 30

#units_meters = False if total_unit != "m" else True
try :
    with open("/home/treadwall/Display/unit.txt","r") as f :
        read_reset = f.read()
        units_meters = True if read_reset == "m" else False # reset on-off fla

except :
    units_meters = False
    save_unit("ft")
    
units_button_text = 'Change to meters' if not units_meters else 'Change to feet'

time_goal_sec = 0
time_goal_min = 0
time_goal_inc = 1
time_goal_max = 60
distance_goal = 0.0
distance_goal_inc = 1
distance_goal_max = 100


time_reached_min = 0
time_reached_sec = 0
distance_reached = 0.0
start_time = False # 2.1
#st_time = 0 #2.1
st_time = int(round(time.time() * 1000))  
##############
#started text
started1 ='''1. Angle:  It is adjusted by a lever on the left side of the unit. Standing on the ground, push down the lever to release the angle, then push the wall/ladder backwards to make steeper. To bring the wall forward, push down the lever and the wall/ladder should move forward on its own but may need a light pull.
2. Speed: It is adjusted by the lever on the right side of the unit. One is slow or stopped, ten is fast. Start slow and adjust to your desired pace when climbing. 
3. Auto-stop system: This will stop the wall or ladder when your feet reach the bottom panel or rung. On the Treadwall there is a sensor behind the wall, and on the Laddermill there is a brake bar at the bottom. Once you start climbing again, the brake will release and the unit will rotate again. 
4. Training Suggestions: See the 'Training' screen in the menu for workout examples.'''

started2 ='''1. To turn on the display, touch the screen or rotate the wall. 
2. When the wall rotates, the display will begin counting distance and time. 
3. Stop moving for ten seconds and the display will pause. When you begin climbing, it will begin to count.
4. Press “Set Goals” to enter either a time or distance goal using the keypad. Select “done” when finished. 
5. With a goal set, the display will count down until you reach your goal. Once the goal is reached, the distance and time you achieved will remain visible. The standard counter will keep counting if the climber continues. 
6. Press “Reset” to clear the counter and the goals. The unit will automatically reset after 5 minutes.
7. In “Menu” you can change units from feet to meters. You can also access some training recommendations.'''

##############
# training text
training ='''
Training on a Treadwall® or Laddermill® is a full body workout. There are many ways to train, but here are a few suggestions.
'''
training1 ='''
Practice your ability to move for longer distances and times without stopping:

1. Complete a lap using all holds or ladder rungs: add multiple laps if you can.
2. Treadwall challenge: Eliminate holds of a certain color and try to complete a lap of the wall not using that color.
3. Laddermill challenge: Try using every other rung or alternating your hand grips.
4. For easier sessions, bring the wall forward. 
5. For more challenging sessions, push the wall back and steeper.
'''
training2 ='''
Lock Off Training (especially for Treadwall training):
For added strength training, try the following protocol.

1. Every time you reach for the next hold, hold your hand over the intended next grip, for 2, 3, 4, or even 5 seconds before grabbing the hold. 
2. This slow, locked off method of training will build strength in your back muscles and help reinforce climbing in control.
'''

training3 ='''
Interval workouts: This workout trains cardiovascular fitness and recovery. 
One set: Climb for 1-2 minutes, then rest for 1 minute.

1. Perform four sets. Then, rest for 5 minutes.
2. Repeat 2 to 5 times.
'''
training4 ='''
Quiet Feet (especially for Treadwall training): 
This exercise will improve your footwork, core strength and foot-eye coordination.

1. When placing your foot on the next foothold or rung, keep your eyes on the foothold or rung until your foot is engaging pressure.
2. Be creative with your foot positions to build strength.
3. This will help you place your feet quietly and deliberately getting the best purchase and downward pressure while climbing.
4. Optional: For every instance of excessive noise from your feet, challenge yourself to that many push-ups or sit-ups at the set’s end.
'''

'''
UI LOOPS
'''

def update_routine():
    global reed_switch_count, reed_switch_state, distance, current_time_ms, current_time_sec
    global current_time_min, idle_cycles_count, idle_time_sec, paused, reset, resetonoff
    global time_reached_min, time_reached_sec, distance_reached, st_time, start_time
    global reed_switch_count0 #, total_unit, total_dist_init 
    # checks if the user is idle
    if idle_cycles_count*refresh_ms*1e-3 > idle_time_sec:
        paused = True

    # logic if reset time is reached
    if resetonoff and (not reset and idle_cycles_count*refresh_ms*1e-3 > reset_time_sec)  :
        reset_reed_count()
        reset = True
        
    # reads the reed switch
    new_reed_switch_reading = GPIO.input(reed_switch_pin)

    # logic for when the user starts moving after a pause
    if paused and not new_reed_switch_reading == reed_switch_state:
        paused = False # clear pause flag
        reset = False # clear reset flag
        idle_cycles_count = 0 # reset cycles count
        st_time = int(round(time.time() * 1000)) - current_time_ms

    # logic for incrementing the reed switch count
    if not paused and not new_reed_switch_reading == reed_switch_state :
        paused = False
        reed_switch_count0 = reed_switch_count
        reed_switch_count = reed_switch_count + 0.5
        reed_switch_state = new_reed_switch_reading
        idle_cycles_count = 0
        run("xset s "+str(reset_time_sec),shell=True) # set screen off to 300 seconds
        run("xset s reset",shell=True) # needed to keep the screen on
    # if the user is not moving, the idle count increases
    else:
        if idle_cycles_count < idle_cycles_max: # stop counting at some point
            idle_cycles_count = idle_cycles_count + 1

    # compute distance
    distance = reed_switch_count*distance_scaling_factor
    
    # calculate time
    if not paused and distance > 0 :
        
        if not start_time : # 2.1
            st_time = int(round(time.time() * 1000))
            start_time = True
        
        current_time_ms =  (int(round(time.time() * 1000)) - st_time )
        current_time_sec = math.floor(current_time_ms/1000) % 60
        current_time_min = math.floor(current_time_ms/60000)

    # update messages
    # if true then display meters
    distance_value = f"Distance: {int(distance)} m " if units_meters else f"Distance: {int(distance)} ft "##
    
    # logic for if the timer is paused
    if paused and (current_time_sec > 0 or  current_time_min > 0):
        pause_message.value = 'Paused' 
        if (distance_goal == 0 and time_goal_sec == 0 ) :
            return
        else :
            time_message.value = 'Time: {:02d}:{:02d}  {}'.format(current_time_min,current_time_sec,distance_value)
            if goal_info.value == '' :
                goal_message.value = ''
                return
    else:
        pause_message.value = ''
        

    # logic if the user reaches their set time goal
    # update
    current_sec = math.floor(current_time_ms/1000)
    if time_goal_sec > 0 and current_sec >= time_goal_sec:
        goal_message.value = 'Goal reached!'
        goal_sec = time_goal_sec % 60
        goal_min = math.floor(time_goal_sec/60)
        units_value = 'm' if units_meters else 'ft'
        goal_info.value = '{2} {3}  {0:02d}:{1:02d}'.format(int(goal_min),int(goal_sec),int(distance_reached),units_value)
        time_message.value = 'Time: {:02d}:{:02d}  {}'.format(current_time_min,current_time_sec,distance_value)

    # logic if the user still not reaches their set time goal calculate tile left
    # update    
    elif time_goal_sec > 0 and not paused :
        diff_time = time_goal_sec*1000 - current_time_ms
        diff_time_sec = math.floor(diff_time/1000)%60
        diff_time_min = math.floor(diff_time/60000)
        goal_message.value = 'Time to Goal :'
        goal_info.value = '{:02d}:{:02d}'.format(int(diff_time_min),int(diff_time_sec))
        distance_reached = distance
        time_message.value = 'Time: {:02d}:{:02d}  {}'.format(current_time_min,current_time_sec,distance_value)
        
    
    # logic if the user reaches their set distance goal
    elif distance_goal > 0 and distance >= distance_goal:
        goal_message.value = 'Goal reached!'
        if units_meters:
            goal_info.value = '{0} m   {1:02d}:{2:02d}'.format(int(distance_goal),int(time_reached_min),int(time_reached_sec))
        else:
            goal_info.value = '{0} ft   {1:02d}:{2:02d}'.format(int(distance_goal),int(time_reached_min),int(time_reached_sec))
        time_message.value = 'Time: {:02d}:{:02d}  {}'.format(current_time_min,current_time_sec,distance_value)

    # logic if the user still not reaches their set distance goal calculate distance left
    # update    
    elif distance_goal > 0 and not paused :
        goal_message.value = 'Distance to Goal :'
        distance_remain = distance_goal - distance                    
        goal_info.value = f"{int(distance_remain)} m " if units_meters else f"{int(distance_remain)} ft "
        time_reached_min = current_time_min
        time_reached_sec = current_time_sec
        time_message.value = 'Time: {:02d}:{:02d}  {}'.format(current_time_min,current_time_sec,distance_value)

    # logic if the user still not start or reset
    # update    
    elif (distance_goal == 0 and time_goal_sec == 0 )  and not paused :
        # if true then display meters
        time_message.value = ''
        goal_message.value = 'Time: {:02d}:{:02d}'.format(current_time_min,current_time_sec)
        goal_info.value = f"Distance: {int(distance)} m" if units_meters else f"Distance: {int(distance)} ft"

def reset_reed_count():
    global reed_switch_count, current_time_ms, current_time_min, current_time_sec, time_goal_sec, distance_goal
    global paused, distance, reed_switch_state, units_meters, time_message, goal_message, goal_info, st_time, start_time
    global reed_switch_count0 #, total_dist_init, total_unit
    reed_switch_count = 0
    reed_switch_count0 = 0
    current_time_ms = 0
    current_time_min = 0
    current_time_sec = 0
    st_time = int(round(time.time() * 1000))    
    time_goal_sec = 0
    distance = 0
    distance_goal = 0
    time_message.value = ""
    goal_message.value = 'Time: {:02d}:{:02d}  '.format(current_time_min,current_time_sec)
    goal_info.value = "Distance: 0 m" if units_meters else "Distance: 0 ft"
    reed_switch_state = GPIO.input(reed_switch_pin)
    paused = False
    start_time = False
    #total_dist_init, total_unit = total_read()

def change_units():
    global units_meters, units_button, distance_scaling_factor, distance_goal, time_message, goal_info
    #global total_dist_init, total_unit
    units_meters = not units_meters
    goal_info_true = False
    time_message_value = time_message.value.split(" ")
    #total_dist_init, total_unit = total_read()
    # check if distance or time is displayed 
    if ("m" in goal_info.value) or ("ft" in goal_info.value) :
        goal_info_true = True
        goal_info_value = goal_info.value.split(" ")

    # 0.3048 meters in a foot
    if units_meters:
        units_button_text = 'Change to feet'
        distance_goal = distance_goal * 0.3048
        '''
        if total_unit != "m" :
            total_dist_init = total_dist_init * 0.3048
            total_unit = "m"
        '''
        distance_scaling_factor = distance_scaling_factor_init * 0.3048
        if len(time_message_value) > 1 : time_message.value = f"Time {time_message_value[1]} Distance {time_message_value[-2]} m"
        if goal_info_true :
            if "Distance" not in goal_info.value :
                goal_info_value0 = float(goal_info_value[0])*0.3048 
                goal_info.value = f"{int(goal_info_value0)} m" if len(goal_info_value)<3 else f"{int(goal_info_value0)} m {goal_info_value[-1]}" 
            else :
                goal_info_value0 = int(float(goal_info_value[1])*0.3048) 
                goal_info.value = f"Distance: {goal_info_value0} m" 

    else:
        units_button_text = 'Change to meters'
        distance_goal = distance_goal / 0.3048
        '''
        if total_unit == "m" :
            total_dist_init = total_dist_init / 0.3048
            total_unit = "ft"
        '''
        distance_scaling_factor = distance_scaling_factor_init
        if len(time_message_value) > 1 : time_message.value = f"Time {time_message_value[1]} Distance {time_message_value[-2]} ft"
        if goal_info_true :
            if "Distance" not in goal_info.value :
                goal_info_value0 = float(goal_info_value[0])/0.3048
                goal_info.value = f"{int(goal_info_value0)} ft" if len(goal_info_value)<3 else f"{int(goal_info_value0)} ft {goal_info_value[-1]}" 
            else :
                goal_info_value0 = int(float(goal_info_value[1])/0.3048) 
                goal_info.value = f"Distance: {goal_info_value0} ft"

    unit_val = "m" if units_meters else "ft"
    save_unit(unit_val)            
    #save_total(total_dist_init, total_unit)        
    # update 
    units_button.text = units_button_text
        
def enter_goals():
    menu_box.hide() #
    main_window.hide()
    goals_input.value = 'min:sec'
    goals_text.value = 'min:sec'
    enter_time()
    goals_box.show()

def enter_menu():    
    global units_meters, units_button, resetonoff    
    units_button.text = 'Change to feet' if units_meters else 'Change to meters'
    read_reset = read_resetonoff()
    reset_onoff_button.text = "Turn autoreset off" if read_reset == True else "Turn autoreset on"
    main_window.hide() 
    goals_box.hide()
    service_box.hide() 
    #admin_input.value = ""
    training_box.hide() 
    training_box1.hide() 
    training_box2.hide() 
    training_box3.hide() 
    training_box4.hide() 
    started_box.hide()
    started_display_box.hide()
    menu_box.show() 

def enter_main():
    global app
    app.tk.attributes("-fullscreen",True)
    main_window.show()
    goals_box.hide()
    menu_box.hide() 
    service_box.hide() 
    training_box.hide() 
    training_box1.hide() 
    training_box2.hide() 
    training_box3.hide() 
    training_box4.hide() 
    started_box.hide()
    started_display_box.hide()

############################################
# setup goals function
last_goals = 'ft'
num_pad = [['1','4','7','0'],['2','5','8','back'],['3','6','9',':']]
inputTime = True

def enter_time():
    global inputTime
    inputTime = True
    goals_text.value = 'min:sec'
    goals_input.value = 'min:sec'
    num_pad[2][3] = ':' # ":" key used only for time setting  

def enter_distance():
    global inputTime, units_meters, distance_scaling_factor, goals_text, goals_input
    inputTime = False # flag if time or distance set
    num_pad[2][3] = '' #  

    if goals_text.value == 'min:sec' :
        goals_text.value = "m" if units_meters else "ft"
        goals_input.value = ''
        #units_meters = False
        #distance_scaling_factor = distance_scaling_factor_init
    if units_meters :
        goals_text.value ='m' 
        goals_input.value = ''
        #distance_scaling_factor = distance_scaling_factor_init
    elif not units_meters :
        goals_text.value = 'ft' 
        goals_input.value = ''
        #distance_scaling_factor = distance_scaling_factor_init * 0.3048
    
def enter_input(x,y):
    global inputTime, goals_input     
    if goals_input.value == "min:sec" : goals_input.value = ''
    if num_pad[x][y] == '' : return
    if num_pad[x][y] == 'back' :
        if goals_input.value != '' :
            x = len(goals_input.value) - 1
            goals_input.value = goals_input.value[:x]
        return
        
    if inputTime :
        if ":" not in goals_input.value  : 
            if len(goals_input.value) > 5 : return
            goals_input.value = goals_input.value + num_pad[x][y]
        elif num_pad[x][y] != ':' :
            v1 = goals_input.value.split(":")[-1]
            if len(v1) < 2 :
                goals_input.value = goals_input.value + num_pad[x][y]
                v2 = goals_input.value.split(":")[-1]
                if len(v2) == 2 and int(v2) > 60:
                    app.warn(' ','Please set sec value less than 60') 
                   
    else :
        if len(goals_input.value) > 5 : return
        goals_input.value = goals_input.value + num_pad[x][y]

    goals_input.cursor_position += 1
       
def enter_done_goals():
    global inputTime, goals_input, distance_goal, time_goal_min, time_goal_sec, units_meters
    global goal_message, goal_info, time_message
    try :
        # reset main screen 
        reset_reed_count()
        time_message.value = goal_message.value + goal_info.value
        # check if no value are set return
        if ("min" in goals_input.value ) or ("sec" in goals_input.value) or (goals_input.value == "") :
            time_message.value = ""
            enter_main()
            return

        if inputTime :            
            if ":" not in goals_input.value :
                time_goal_min = int(goals_input.value)
                time_goal_sec = time_goal_min *60
                time_sec = 0
            else :                
                time_value = goals_input.value.split(":")
                time_goal_min = int(time_value[0])
                time_goal_sec = int(time_value[-1]) + time_goal_min *60
                time_sec = int(time_value[-1])

            goal_message.value = 'Time to Goal :'           
            goal_info.value = '{:02d}:{:02d}'.format(time_goal_min, time_sec)
            distance_goal = 0.0

        else :
            distance_goal = float(goals_input.value)
            time_goal_sec = 0
            time_goal_min = 0
            goal_message.value = 'Distance to Goal :'           
            goal_meter = 'm' if units_meters else 'ft'
            goal_info.value = '{0} {1}'.format(int(distance_goal),goal_meter)
   
    except Exception as e:
        print("error setup goals ",str(e))
        
    enter_main()

#####################################################################################
# menu command

def enter_menu_done():
    enter_main()

def enter_started():
    menu_box.hide()
    main_window.hide()
    started_display_box.hide()
    textbox1.value = started1
    started_box.show()
    
def enter_training():
    menu_box.hide()
    main_window.hide()
    textbox_training.value = training
    training_box.show()

def enter_resetonoff() :
    global resetonoff, reset_onoff_button
    reset_onoff_button.text = "Turn autoreset on" if resetonoff else "Turn autoreset off"
    resetonoff = not resetonoff
    #read_reset = read_resetonoff()
    #resetonoff1 = True if read_reset== "true" else False    
    save_resetonoff(resetonoff)
    menu_box.show()


def service() :
    global total_unit, total_dist_init
    menu_box.hide()
    main_window.hide()
    #total_dist_init1, total_unit1 = total_read()
    #textbox_service1.value = "%.2f" %total_dist_init1
    #textbox_service2.value = total_unit1
    service_box.show()
   
################################################################################
# Getting Started  command
def enter_done_started():
    started_box.hide()
    enter_main()

def display_started():
    menu_box.hide()
    main_window.hide()
    started_box.hide()
    textbox2.value = started2
    started_display_box.show()

################################################################################
# Training  command
def enter_done_training():
    training_box1.hide()
    training_box2.hide()
    training_box3.hide()
    training_box4.hide()
    training_box.hide()
    enter_main()
    
def endurance_training():
    training_box.hide()
    training_box2.hide()
    training_box3.hide()
    training_box4.hide()
    textbox1_training.value = training1
    training_box1.show()

def lock_off_training():
    training_box.hide()
    training_box1.hide()
    training_box3.hide()
    training_box4.hide()
    textbox2_training.value = training2
    training_box2.show()
    
def interval_workouts():
    training_box.hide()
    training_box1.hide()
    training_box2.hide()
    training_box4.hide()
    textbox3_training.value = training3
    training_box3.show()

def quiet_feet():
    training_box.hide()
    training_box1.hide()
    training_box2.hide()
    training_box3.hide()
    textbox4_training.value = training4
    training_box4.show()
'''
RPI SETUP
'''
def init_io():
    # native Pi GPIO
    GPIO.setwarnings(False)
    GPIO.setmode(GPIO.BCM)
    # set as inputs with pull ups
    GPIO.setup(reed_switch_pin, GPIO.IN, pull_up_down = GPIO.PUD_UP) # reed switch

if __name__ == "__main__":

    print('init IO')
    try:
        init_io()
    except:
        print('IO Issues')
    print('init finished')
    print('running state machine')
    try:
        app = App(title='TREADWALL')
        app.bg = "#999999"
        # main
        # NOTE: the order of definition below is important
        main_window = Box(app, layout='grid')
        empty_box1 = Text(main_window,width=5, height = 1, grid=[0,0])
        time_message = Text(main_window, grid=[0,1]) 
        time_message.text_size = 35
        empty_box2 = Text(main_window,width=5, height = 1, grid=[0,2])
        pause_message = Text(main_window, grid=[0,3]) 
        pause_message.text_size = 40        
        empty_box3 = Text(main_window,width=5, height = 1, grid=[0,4])
        # goal messages
        goal_message = Text(main_window, grid=[0,5]) 
        goal_message.text_size = 45 
        goal_info = Text(main_window, grid=[0,6]) 
        goal_info.text_size = 45
        empty_box4 = Text(main_window,width=5, height = 2, grid=[0,7])        
        empty_box4.text_size = 40

        # Schedule call to runStateMachine() every 10ms
        empty_box4.repeat(refresh_ms, update_routine)  

        # buttons on the main screen
        main_button_box = Box(main_window, layout='grid', grid=[0,8],align='bottom')
        started_button = PushButton(main_button_box, text='Getting Started', width = 11, command=enter_started, grid=[0,0])
        started_button.text_size = button_text_size
        empty0_message = Text(main_button_box, text='  ', grid=[1,0])
        goals_button = PushButton(main_button_box, text='Set Goals', width = 7, command=enter_goals, grid=[2,0])
        goals_button.text_size = button_text_size
        empty1_message = Text(main_button_box, text='  ', grid=[3,0])
        reset_button = PushButton(main_button_box, text='Reset', width = 5, command=reset_reed_count, grid=[4,0])
        reset_button.text_size = button_text_size
        empty2_message = Text(main_button_box, text='  ', grid=[5,0])
        menu_button = PushButton(main_button_box, text='Menu', width = 5, command=enter_menu, grid=[6,0])
        menu_button.text_size = button_text_size

        ################################################################################################################
        # setup goals
        goals_box = Box(app, layout='grid')
        title_text = Text(goals_box, text='Goals', grid=[0,0])
        title_text.text_size = 30
        lin1_box = Box(goals_box, layout='grid',grid=[0,1])
        goals_input = TextBox(lin1_box, text='min:sec', width = 10,grid=[0,0])
        goals_input.text_size = 16
        empty_goalsl1 = Text(lin1_box,text='  ', grid=[1,0])
        goals_text = Text(lin1_box, text='min:sec',grid=[2,0])
        goals_text.text_size = 16
        empty_goals1 = Text(goals_box,width=5, height = 1, grid=[0,2])

        button_box = Box(goals_box, layout='grid',grid=[0,3], border=2)
        for x in range(3) :
            for y in range(4) :
                num_but = PushButton(button_box, text=num_pad[int(x)][int(y)], width = 4, command= enter_input, grid=[int(x),int(y)],args=[x,y])
                num_but.text_size = 14
        empty_goals2 = Text(goals_box,width=5, height = 1, grid=[0,4])
        lin2_box = Box(goals_box, layout='grid',grid=[0,5])
        time_button = PushButton(lin2_box, text='Time', width = 10,command= enter_time,grid=[0,0])
        time_button.text_size = button_text_size #17
        empty_goalsl2 = Text(lin2_box, text='   ',grid=[1,0])
        distance_button = PushButton(lin2_box, text='Distance', width = 10, command= enter_distance,grid=[2,0])
        distance_button.text_size = button_text_size #17
        empty_goals3 = Text(goals_box,width=5, grid=[0,6])
        done_goals_button = PushButton(goals_box, text='Done', command=enter_done_goals, grid=[0,7])
        done_goals_button.text_size = button_text_size
        ################################################################################################################
        # service
        
        service_box = Box(app, layout='grid')
        empty_service0 = Text(service_box,text=' ', height = 1, grid=[0,0])
        title_text = Text(service_box, text='Service', grid=[0,1])
        title_text.text_size = 30
        empty_service = Text(service_box,width=5, height = 1, grid=[0,2])
        empty_service12 = Text(service_box,width=5, height = 1, grid=[0,3])
        contact_box = Box(service_box, layout='grid',grid=[0,4])
        contact_info = Text(contact_box, text='Contact Information of Company  : ',grid=[0,0])
        contact_info.text_size = 25
        empty_service13 = Text(contact_box,width=5, height = 1, grid=[0,1])
        contact_info1 = Text(contact_box, text='Treadwall Fitness',grid=[0,2])
        contact_info1.text_size = 20
        empty_service14 = Text(contact_box,width=5, height = 1, grid=[0,3])
        contact_info2 = Text(contact_box, text='781-961-5200',grid=[0,4])
        contact_info2.text_size = 20
        empty_service15 = Text(contact_box,width=5, height = 1, grid=[0,5])
        contact_info3 = Text(contact_box, text='sales@treadwallfitness.com',grid=[0,6])
        contact_info3.text_size = 20
        empty_service16 = Text(contact_box,width=5, height = 1, grid=[0,7])
        contact_info4 = Text(contact_box, text='www.treadwallfitness.com',grid=[0,8])
        contact_info4.text_size = 20
        empty_service2 = Text(service_box,width=5, height = 1, grid=[0,5])
        done_menu_button = PushButton(service_box, text=' Done ', command=enter_menu_done, grid=[0,6])
        done_menu_button.text_size = button_text_size
        

        ########################################################################
        # menu window
        menu_box = Box(app, layout='grid')
        menu_text = Text(menu_box, text='Menu', grid=[0,0])
        menu_text.text_size = text_size
        empty_menu0 = Text(menu_box, text='     ',grid=[0,1])
        menu1_box = Box(menu_box, layout='grid', grid=[0,2])
        started_button = PushButton(menu1_box, text='Getting Started', command= enter_started, grid=[0,0])
        started_button.text_size = button_text_size
        empty_menu1 = Text(menu1_box, text='        ',grid=[1,0])
        training_button = PushButton(menu1_box, text='Training', command=enter_training, grid=[2,0])
        training_button.text_size = button_text_size
        empty_menu2 = Text(menu_box, text='     ', grid=[0,3])
        menu2_box = Box(menu_box, layout='grid', grid=[0,4])
        empty_menu4 = Text(menu2_box, text='     ',grid=[1,0])
        units_button = PushButton(menu2_box, text='Change to meters', command=change_units, grid=[2,0]) 
        units_button.text_size = button_text_size 
        empty_menu5 = Text(menu2_box, text='    ',grid=[3,0])
        
        total_button = PushButton(menu2_box, text='Service', command=service, grid=[4,0]) 
        total_button.text_size = button_text_size 
        empty_menu5 = Text(menu2_box, text='    ',grid=[5,0])
        
        reset_onoff_button = PushButton(menu2_box, text='Turn autoreset off', command=enter_resetonoff, grid=[6,0])
        reset_onoff_button.text_size = button_text_size
        empty_menu3 = Text(menu_box, text='     ', grid=[0,5])
        done_menu_button = PushButton(menu_box, text=' Done ', command=enter_menu_done, grid=[0,6])
        done_menu_button.text_size = button_text_size
        ########################################################################
        # Getting Started
        started_box = Box(app, layout='grid')
        title1_message = Text(started_box, text="How to use the Treadwall® and Laddermill®. :", grid=[0,0], size=20)
        title1_message.text_size= 25
        title_empty = Text(started_box, text="", grid=[0,1])
        title_empty.text_size=1
        textbox1 = TextBox(started_box, multiline=True, width=64, height=15, scrollbar=False, text=started1, grid=[0,2])
        textbox1.text_size=15
        textbox1.tk['wrap'] = 'word'
        title_started_empty1 = Text(started_box, text="", grid=[0,3])
        title_started_empty1.text_size=5
        started_button_box = Box(started_box, layout='grid', grid=[0,4])
        display_started_button = PushButton(started_button_box, text='Using Display', command=display_started, grid=[0,0])
        display_started_button.text_size = button_text_size
        started_empty = Text(started_button_box, text="      ", grid=[1,0])
        done_started_button = PushButton(started_button_box, text='Done', command=enter_done_started, grid=[2,0])
        done_started_button.text_size = button_text_size
        ########################################################################
        # Getting Started- Display
        started_display_box = Box(app, layout='grid')
        title2_message = Text(started_display_box, text="How to use the display :", grid=[0,0],size=20)
        title2_message.text_size= 25
        title_display_empty = Text(started_display_box, text="", grid=[0,1])
        title_display_empty.text_size=1
        textbox2 = TextBox(started_display_box, multiline=True, width=64, height=15,scrollbar=False, text=started2,grid=[0,2])
        textbox2.text_size=15
        textbox2.tk['wrap'] = 'word'
        title_display_empty1 = Text(started_display_box, text="", grid=[0,3])
        title_display_empty1.text_size=5
        display_button_box = Box(started_display_box, layout='grid', grid=[0,4])
        enter_started_button = PushButton(display_button_box, text='Using Treadwall or Laddermill', command=enter_started, grid=[0,0])
        enter_started_button.text_size = button_text_size
        display_empty = Text(display_button_box, text="     ", grid=[1,0])
        done_display_started = PushButton(display_button_box, text='Done', command=enter_done_started, grid=[2,0])
        done_display_started.text_size = button_text_size
        ########################################################################
        ########################################################################
        # Training
        training_box = Box(app, layout='grid')
        title_training = Text(training_box, text="Training", grid=[0,0], size=20)
        title_training.text_size= 40
        title_training_empty = Text(training_box, text="", grid=[0,1])
        title_training_empty.text_size=5
        textbox_training = TextBox(training_box, multiline=True, width=45, height=8, scrollbar=False, text=training, grid=[0,2])
        textbox_training.text_size=20
        textbox_training.tk['wrap'] = 'word'
        title_training_empty1 = Text(training_box, text="", grid=[0,3])
        title_training_empty1.text_size=5
        training_button_box = Box(training_box, layout='grid', grid=[0,4])
        training_button1 = PushButton(training_button_box, text='Endurance', command=endurance_training, grid=[0,0])
        training_button1.text_size = button_text_size
        training_empty1 = Text(training_button_box, text=" ", grid=[1,0])
        training_button2 = PushButton(training_button_box, text='Strength', command=lock_off_training, grid=[2,0])
        training_button2.text_size = button_text_size
        training_empty2 = Text(training_button_box, text=" ", grid=[3,0])
        training_button3 = PushButton(training_button_box, text='Intervals', command=interval_workouts, grid=[4,0])
        training_button3.text_size = button_text_size
        training_empty3 = Text(training_button_box, text=" ", grid=[5,0])
        training_button4 = PushButton(training_button_box, text='Technique', command=quiet_feet, grid=[6,0])
        training_button4.text_size = button_text_size
        training_empty0 = Text(training_box, text="     ", grid=[0,5])
        done_training_button = PushButton(training_box, text='Done', command=enter_done_training, grid=[0,6])
        done_training_button.text_size = button_text_size
        # Training1
        training_box1 = Box(app, layout='grid')
        title_training1 = Text(training_box1, text="Endurance", grid=[0,0], size=20)
        title_training1.text_size= 30
        title_training1_empty = Text(training_box1, text="", grid=[0,1])
        title_training1_empty.text_size=1
        textbox1_training = TextBox(training_box1, multiline=True, width=64, height=15, scrollbar=False, text=training1, grid=[0,2])
        textbox1_training.text_size=15
        textbox1_training.tk['wrap'] = 'word'
        title_training1_empty1 = Text(training_box1, text="", grid=[0,3])
        title_training1_empty1.text_size=5
        training_button_box1 = Box(training_box1, layout='grid', grid=[0,4])
        training1_button4 = PushButton(training_button_box1, text='Endurance', command=endurance_training, grid=[0,0])
        training1_button4.text_size = button_text_size
        training1_empty1 = Text(training_button_box1, text=" ", grid=[1,0])
        training1_button1 = PushButton(training_button_box1, text='Strength', command=lock_off_training, grid=[2,0])
        training1_button1.text_size = button_text_size
        training1_empty1 = Text(training_button_box1, text=" ", grid=[3,0])
        training1_button2 = PushButton(training_button_box1, text='Intervals', command=interval_workouts, grid=[4,0])
        training1_button2.text_size = button_text_size
        training1_empty2 = Text(training_button_box1, text=" ", grid=[5,0])
        training1_button3 = PushButton(training_button_box1, text='Technique', command=quiet_feet, grid=[6,0])
        training1_button3.text_size = button_text_size
        training1_empty3 = Text(training_button_box1, text=" ", grid=[7,0])
        training1_empty3.text_size = 5
        done_training1_button = PushButton(training_button_box1, text='Done', command=enter_done_training, grid=[8,0])
        done_training1_button.text_size = button_text_size
        # Training2
        training_box2 = Box(app, layout='grid')
        title_training2 = Text(training_box2, text="Strength", grid=[0,0], size=20)
        title_training2.text_size= 30
        title_training2_empty = Text(training_box2, text="", grid=[0,1])
        title_training2_empty.text_size=1
        textbox2_training = TextBox(training_box2, multiline=True, width=64, height=15, scrollbar=False, text=training2, grid=[0,2])
        textbox2_training.text_size=15
        textbox2_training.tk['wrap'] = 'word'
        title_training2_empty1 = Text(training_box2, text="", grid=[0,3])
        title_training2_empty1.text_size=5
        training_button_box2 = Box(training_box2, layout='grid', grid=[0,4])
        training2_button1 = PushButton(training_button_box2, text='Endurance', command=endurance_training, grid=[0,0])
        training2_button1.text_size = button_text_size
        training2_empty1 = Text(training_button_box2, text=" ", grid=[1,0])
        training2_button4 = PushButton(training_button_box2, text='Strength', command=lock_off_training, grid=[2,0])
        training2_button4.text_size = button_text_size
        training2_empty4 = Text(training_button_box1, text=" ", grid=[3,0])
        training2_button2 = PushButton(training_button_box2, text='Intervals', command=interval_workouts, grid=[4,0])
        training2_button2.text_size = button_text_size
        training2_empty2 = Text(training_button_box2, text=" ", grid=[5,0])
        training2_button3 = PushButton(training_button_box2, text='Technique', command=quiet_feet, grid=[6,0])
        training2_button3.text_size = button_text_size
        training2_empty3 = Text(training_button_box2, text=" ", grid=[7,0])
        training2_empty3.text_size = 5
        done_training2_button = PushButton(training_button_box2, text='Done', command=enter_done_training, grid=[8,0])
        done_training2_button.text_size = button_text_size
        # Training3
        training_box3 = Box(app, layout='grid')
        title_training3 = Text(training_box3, text="Intervals", grid=[0,0], size=20)
        title_training3.text_size= 30
        title_training3_empty = Text(training_box3, text="", grid=[0,1])
        title_training3_empty.text_size=1
        textbox3_training = TextBox(training_box3, multiline=True, width=64, height=15, scrollbar=False, text=training3, grid=[0,2])
        textbox3_training.text_size=15
        textbox3_training.tk['wrap'] = 'word'
        title_training3_empty1 = Text(training_box3, text="", grid=[0,3])
        title_training3_empty1.text_size=5
        training_button_box3 = Box(training_box3, layout='grid', grid=[0,4])
        training3_button1 = PushButton(training_button_box3, text='Endurance', command=endurance_training, grid=[0,0])
        training3_button1.text_size = button_text_size
        training3_empty1 = Text(training_button_box3, text=" ", grid=[1,0])
        training3_button2 = PushButton(training_button_box3, text='Strength', command=lock_off_training, grid=[2,0])
        training3_button2.text_size = button_text_size
        training3_empty2 = Text(training_button_box3, text=" ", grid=[3,0])
        training3_button4 = PushButton(training_button_box3, text='Intervals', command=interval_workouts, grid=[4,0])
        training3_button4.text_size = button_text_size
        training3_empty4 = Text(training_button_box3, text=" ", grid=[5,0])
        training3_button3 = PushButton(training_button_box3, text='Technique', command=quiet_feet, grid=[6,0])
        training3_button3.text_size = button_text_size
        training3_empty3 = Text(training_button_box3, text=" ", grid=[7,0])
        training3_empty3.text_size = 5
        done_training3_button = PushButton(training_button_box3, text='Done', command=enter_done_training, grid=[8,0])
        done_training3_button.text_size = button_text_size
        # Training4
        training_box4 = Box(app, layout='grid')
        title_training4 = Text(training_box4, text="Technique", grid=[0,0], size=20)
        title_training4.text_size= 30
        title_training4_empty = Text(training_box4, text="", grid=[0,1])
        title_training4_empty.text_size=1
        textbox4_training = TextBox(training_box4, multiline=True, width=64, height=15, scrollbar=False, text=training4, grid=[0,2])
        textbox4_training.text_size=15
        textbox4_training.tk['wrap'] = 'word'
        title_training4_empty1 = Text(training_box4, text="", grid=[0,3])
        title_training4_empty1.text_size=5
        training_button_box4 = Box(training_box4, layout='grid', grid=[0,4])
        training4_button1 = PushButton(training_button_box4, text='Endurance', command=endurance_training, grid=[0,0])
        training4_button1.text_size = button_text_size
        training4_empty1 = Text(training_button_box4, text=" ", grid=[1,0])
        training4_button2 = PushButton(training_button_box4, text='Strength', command=lock_off_training, grid=[2,0])
        training4_button2.text_size = button_text_size
        training4_empty2 = Text(training_button_box4, text=" ", grid=[3,0])
        training4_button3 = PushButton(training_button_box4, text='Intervals', command=interval_workouts, grid=[4,0])
        training4_button3.text_size = button_text_size
        training4_empty3 = Text(training_button_box4, text=" ", grid=[5,0])
        training4_empty3.text_size = 5
        training4_button4 = PushButton(training_button_box4, text='Technique', command=quiet_feet, grid=[6,0])
        training4_button4.text_size = button_text_size
        training4_empty4 = Text(training_button_box4, text=" ", grid=[7,0])
        training4_empty4.text_size = 5
        done_training4_button = PushButton(training_button_box4, text='Done', command=enter_done_training, grid=[8,0])
        done_training4_button.text_size = button_text_size
        ########################################################################
        # show main screen and hide all others  screens when you load onto the main page
        enter_main()

        # show the app in full screen without the top menu bar
        app.tk.attributes("-fullscreen",True)
        width = app.tk.winfo_screenwidth()
        height = app.tk.winfo_screenheight()
        app.tk.config(cursor="none")
        app.tk.geometry("%dx%d" % (width, height))
        app.display()
        
    except KeyboardInterrupt:
        pass
    
    print('PROGRAM EXIT')
    GPIO.cleanup()
