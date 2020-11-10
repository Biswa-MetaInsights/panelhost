import random

class integrityValue():

    def __new__(cls, userValue):
        return (userValue+random.randint(0,10))*(random.randint(1,5))