import numpy as np
import cv2


#img = cv2.imread('images/test-receipt.jpg')
#
#stacked_image = process_image(img)
#
#plt.imshow(cv2.cvtColor(
#    stacked_image,
#    cv2.COLOR_RGB2BGR))
#plt.show()

#document_scanner()


img_gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

img_processed = process_image_with_settings(img_gray, settings):
cv2.imshow("Video", img_processed)
cv2.waitKey(1)
cv2.destroyAllWindows()

kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (edk, edk))
img_dilated = cv2.dilate(img_edges, kernel=kernel, iterations=di)
img_closed = cv2.erode(img_dilated, kernel=kernel, iterations=ei)

corners = find_largest_4d_countour(img_closed)
img_contours = img.copy()
img_contours = cv2.drawContours(img_contours, corners, -1, (255, 0, 0), 20)

img_warped = img.copy()


def process_image_with_settings(img, settings):
    img_gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    img_blurred = cv2.GaussianBlur(img_gray, ksize=(gbk, gbk), sigmaX=gbs)
    img_edges = cv2.Canny(img_blurred, ct1, ct2)

    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (edk, edk))
    img_dilated = cv2.dilate(img_edges, kernel=kernel, iterations=di)
    img_closed = cv2.erode(img_dilated, kernel=kernel, iterations=ei)

    corners = find_largest_4d_countour(img_closed)
    img_contours = img.copy()
    img_contours = cv2.drawContours(img_contours, corners, -1, (255, 0, 0), 20)

    img_warped = img.copy()
    print('corners.size:', corners.size)
    if len(corners) == 4:
        img_warped = warp_image(img_warped, corners)


def draw_contours(binarized_image, contour_minimum_area=1000):
    contours, hierarchy = cv2.findContours(binarized_image, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    img_contours = cv2.cvtColor(binarized_image, cv2.COLOR_GRAY2BGR)
    for contour in contours:
        area = cv2.contourArea(contour)
        if area > contour_minimum_area:
            cv2.drawContours(img_contours, contour, -1, (255, 0, 0), 3)
    return img_contours


def find_largest_4d_countour(binarized_image, contour_minimum_area=500):
    largest_contour = np.array([])
    max_area = 0
    contours, hierarchy = cv2.findContours(binarized_image, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    for contour in contours:
        area = cv2.contourArea(contour)
        if area > contour_minimum_area:
            peri = cv2.arcLength(contour, True)
            approx = cv2.approxPolyDP(contour, 0.02 * peri, True)
            if area > max_area and len(approx) == 4:
                largest_contour = approx
                max_area = area
    print(f'LargestContour[{len(largest_contour)}]:', largest_contour)
    return largest_contour


def draw_largest_4d_countour(binarized_image, contour_minimum_area=2000):
    contour = find_largest_4d_countour(binarized_image, contour_minimum_area)
    img_contours = cv2.cvtColor(binarized_image, cv2.COLOR_GRAY2BGR)
    return cv2.drawContours(img_contours, contour, -1, (255, 0, 0), 20)


# reorder (for correct input to warping function
def _reorder_corner_points(page_corner_points):
    page_corner_points = page_corner_points.reshape((4, 2))
    reordered_points = np.zeros((4, 1, 2), np.int32)

    pair_sum = page_corner_points.sum(1)
    reordered_points[0] = page_corner_points[np.argmin(pair_sum)]
    reordered_points[3] = page_corner_points[np.argmax(pair_sum)]

    pair_diff = np.diff(page_corner_points, axis=1)
    reordered_points[1] = page_corner_points[np.argmin(pair_diff)]
    reordered_points[2] = page_corner_points[np.argmax(pair_diff)]
    return reordered_points

def warp_image(img, page_corners):
    page_corners = _reorder_corner_points(page_corners)
    img_width = img.shape[1]
    img_height = img.shape[0]
    old_corner_points = np.float32(page_corners)
    new_corner_points = np.float32([[0, 0], [img_width, 0],
                                    [0, img_height], [img_width, img_height]])
    matrix = cv2.getPerspectiveTransform(old_corner_points, new_corner_points)
    img_warped= cv2.warpPerspective(img, matrix, (img_width, img_height))
    #img_cropped = imgOutput[20:img.shape[0] - 20, 20:img.shape[1] - 20]
    #img_cropped = cv2.resize(img_cropped, (widthImg, heightImg))
    return img_warped
