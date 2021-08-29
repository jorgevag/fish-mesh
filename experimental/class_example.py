class Dog:
    def __init__(self):
        self.age = 10

    def growing_older(self, year_passed):
        self.age += year_passed


if __name__ == "__main__":
    a_dog = Dog()
    print("dog age is:", a_dog.age)
    years_passed = 2
    a_dog.growing_older(years_passed)
    print(f"after {years_passed} years, dog age is:", a_dog.age)
