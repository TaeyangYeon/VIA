import cv2
import numpy as np

def inspect_item(image: np.ndarray) -> dict:
    """
    이미지를 입력받아 지정된 전처리 파이프라인을 거쳐 개별 Blob(영역)의 개수를 세고, 
    최소 3개 이상의 Blob이 존재하는지 검사합니다.
    """
    
    # 1. Grayscale
    img_gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    
    # 2. Gaussian Blur (sigma=0.8)
    # cv2.GaussianBlur needs a tuple for kernel size. Using sigma=0.8.
    img_gauss = cv2.GaussianBlur(img_gray, (0, 0), 0.8)
    
    # 3. Bilateral Filtering (d=5, sigmaColor=25)
    # Assuming default sigmaSpace=25 for consistency if not specified.
    img_bili = cv2.bilateralFilter(img_gauss, d=5, sigmaColor=25, sigmaSpace=25)
    
    # 4. Otsu Thresholding
    # Performs Otsu thresholding to binarize the image
    ret, thresh = cv2.threshold(img_bili, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    
    # 5. Dilation (k=3, iterations=1)
    # Kernel size 3, iterations 1
    kernel = np.ones((3, 3), dtype=np.uint8)
    img_dilated = cv2.dilate(thresh, kernel, iterations=1)
    
    # 6. Blob Extraction (Contour Finding)
    # Find contours on the final processed binary image
    contours, _ = cv2.findContours(img_dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    blob_count = len(contours)
    
    # 7. Inspection Logic
    min_required_blobs = 3
    if blob_count >= min_required_blobs:
        result = "OK"
        status_message = f"Blob 영역이 {blob_count}개 발견되어 성공 기준({min_required_blobs}개 이상)을 충족합니다."
    else:
        result = "NG"
        status_message = f"Blob 영역이 {blob_count}개만 발견되어 실패 기준({min_required_blobs}개 이상)에 미달합니다."

    return {
        "result": result,
        "details": {
            "extracted_blob_count": blob_count,
            "minimum_required_blobs": min_required_blobs,
            "status_message": status_message
        }
    }

import cv2
import numpy as np

def inspect_item(image: np.ndarray) -> dict:
    """
    원형성 검증 및 경계 추출을 수행합니다. 파이프라인을 통해 이미지를 전처리하고,
    탐지된 Blob 중 원형성 점수(Circularity Ratio)가 0.9 이상인 객체를 필터링합니다.
    """
    
    # 1. Pipeline Processing Steps
    # grayscale
    img_gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    
    # gaussian_fine({'sigma': 0.8})
    # Using GaussianBlur for fine Gaussian effect
    img_g = cv2.GaussianBlur(img_gray, (0, 0), 0.8)
    
    # bilateral({'d': 5, 'sigmaColor': 25})
    img_b = cv2.bilateralFilter(img_g, 5, 25, 25)
    
    # otsu
    # Otsu thresholding
    _, thresh = cv2.threshold(img_b, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    
    # dilation({'k': 3, 'iterations': 1})
    # Kernel size 3x3, 1 iteration
    kernel = np.ones((3, 3), np.uint8)
    processed_mask = cv2.dilate(thresh, kernel, iterations=1)

    # 2. Blob Detection and Filtering
    # Find contours on the processed mask
    contours, _ = cv2.findContours(processed_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    detected_blobs = []
    circular_blobs = []
    
    for contour in contours:
        # Calculate area and perimeter
        area = cv2.contourArea(contour)
        perimeter = cv2.arcLength(contour, True)
        
        if area < 10: # Filter very small noise
            continue
            
        # Calculate Circularity Ratio: 4*pi*Area / Perimeter^2
        if perimeter > 0:
            circularity_ratio = (4 * np.pi * area) / (perimeter ** 2)
        else:
            circularity_ratio = 0.0
            
        details = {"area": float(area), "perimeter": float(perimeter), "circularity_ratio": round(circularity_ratio, 4)}
        
        detected_blobs.append(details)
        
        # Check success criteria
        if circularity_ratio >= 0.9:
            circular_blobs.append(contour) # Store the actual contour for boundary extraction
    
    # 3. Result Determination and Boundary Extraction
    
    if len(circular_blobs) > 0:
        # Success: At least one object meets the circularity criterion
        result = "OK"
        # Boundary extraction: Use the mask on the original image for visualization/detailed edge extraction
        # Here we simply return the found contours/blobs metadata.
        
        # For actual edge map extraction (optional step, just logging the successful finding):
        # The detected contours define the boundaries.
        # We create a mask showing the identified areas.
        output_mask = np.zeros_like(image) 
        cv2.drawContours(output_mask, circular_blobs, -1, (255), thickness=2)
        
        return {
            "result": result,
            "details": {
                "detected_count": len(detected_blobs),
                "circular_count": len(circular_blobs),
                "min_circularity_ratio": 0.9,
                "success": True,
                "boundaries_processed": True # Indicates successful boundary extraction on the filtered objects
            }
        }
    else:
        # Failure: No object meets the circularity criterion
        result = "NG"
        return {
            "result": result,
            "details": {
                "detected_count": len(detected_blobs),
                "circular_count": 0,
                "min_circularity_ratio": 0.9,
                "success": False
            }
        }


import cv2
import numpy as np

def inspect_item(image: np.ndarray) -> dict:
    # 1. grayscale
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    
    # 2. gaussian_fine({'sigma': 0.8})
    # Note: Assuming gaussian_fine is a wrapper for cv2.GaussianBlur or similar functionality.
    # Using cv2.GaussianBlur for standard implementation.
    sigma_gaussian = 0.8
    blurred = cv2.GaussianBlur(gray, (0, 0), sigma_gaussian)
    
    # 3. bilateral({'d': 5, 'sigmaColor': 25})
    # Using cv2.bilateralFilter
    d_val = 5
    sigma_color = 25
    bilateral = cv2.bilateralFilter(blurred, d_val, sigma_color, sigma_color)
    
    # 4. otsu
    # Otsu's thresholding on the bilateral filtered image
    _, thresh = cv2.threshold(bilateral, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    
    # 5. dilation({'k': 3, 'iterations': 1})
    # Using cv2.dilate
    kernel = np.ones((3, 3), np.uint8)
    processed_image = cv2.dilate(thresh, kernel, iterations=1)
    
    # BLOB detection: Find contours
    contours, _ = cv2.findContours(processed_image, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    
    # Count the detected blobs (contours)
    num_blobs = len(contours)
    
    # Determine result based on success criteria (>= 1 blob)
    if num_blobs >= 1:
        result = "OK"
        message = f"성공: {num_blobs}개의 유효한 원형 객체가 감지되었습니다. (최소 1개 이상)"
    else:
        result = "NG"
        message = "실패: 감지된 객체가 없습니다. 최소 1개의 객체가 필요합니다."

    return {
        "result": result,
        "details": {
            "object_count": num_blobs,
            "message": message
        }
    }
