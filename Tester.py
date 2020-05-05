import numpy as np

def main():

    check = np.array([1,2,3,4,5,6,7,8,9,10])
    print(check)
    bad = [1,5,9]
    for b in bad:
        new_check = check[np.where(check != b)]
        check = new_check
    print(check)


if __name__ == "__main__":
    main()
