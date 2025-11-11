import random

number = random.randint(1,20)
found = False
chances = 0

while(found!=True):

    num = int(input("Enter a number: "))
    
    if(number == num):
        print("Currect guess!!")
        found = True
        break
    else:
        print("Wrong guess!!")
    chances+=1
    if(chances>=5):
        break
if(found == True):
    print(f"You have gussed the currect number!! \nNumber was {number}")
else:
    print(f"You have lost the game.\nThe number is: {number}")