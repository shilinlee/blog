"""
start + 1 < end: 相邻或者相交退出循环
mid = start + (end - start) / 2: 中间位置
"""


def binarySearch(A: list, target: int):
    if not A:
        return -1
    start = 0
    end = len(A) - 1
    mid = None

    while (start + 1 < end):
        mid = int(start + (end - start) / 2)
        if A[mid] == target:
            end = mid
        elif A[mid] < target:
            start = mid
        else:
            end = mid
    if A[start] == target:
        return start
    elif A[end] == target:
        return end
    return -1


if __name__ == "__main__":
    print(binarySearch([1, 2, 3, 4, 5], 3))
