import cv2
import mediapipe as mp

# MediaPipe Pose setup
mp_pose = mp.solutions.pose
mp_drawing = mp.solutions.drawing_utils

# Load image
image_path = "input.jpg"   # তোমার image path
image = cv2.imread(image_path)
image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

with mp_pose.Pose(static_image_mode=True) as pose:
    results = pose.process(image_rgb)

    if results.pose_landmarks:
        landmarks = results.pose_landmarks.landmark

        # 3 specific points
        nose = landmarks[mp_pose.PoseLandmark.NOSE]
        left_shoulder = landmarks[mp_pose.PoseLandmark.LEFT_SHOULDER]
        right_shoulder = landmarks[mp_pose.PoseLandmark.RIGHT_SHOULDER]

        h, w, _ = image.shape

        points = {
            "nose": (int(nose.x * w), int(nose.y * h)),
            "left_shoulder": (int(left_shoulder.x * w), int(left_shoulder.y * h)),
            "right_shoulder": (int(right_shoulder.x * w), int(right_shoulder.y * h)),
        }

        # Draw points
        for name, (x, y) in points.items():
            cv2.circle(image, (x, y), 6, (0, 255, 0), -1)
            cv2.putText(image, name, (x+5, y-5),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0,255,0), 1)

        print("Detected points:", points)

    else:
        print("No person detected")

# Show image
cv2.imshow("3 Points Detection", image)
cv2.waitKey(0)
cv2.destroyAllWindows()
