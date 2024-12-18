import cv2
import threading
from playsound import playsound
from ultralytics import YOLO
import numpy as np

# Constantes
ALERT_FILE = "./sound.mp3"
ALERT_REPEATS = 5
DATA_PATH = "./dataSet/data.yaml"
MODEL_PATH = "./runs/detect/train/weights/best.pt"
WARNING_IMAGE_PATH = "./alert.png"

warning_img = cv2.imread(WARNING_IMAGE_PATH)

def train_model(data_path: str, epochs: int) -> None:
    try:
        model = YOLO("./yolov8m.pt")
        model.train(data=data_path, epochs=epochs)
        print("Entraînement terminé.")
    except Exception as e:
        print(f"Erreur lors de l'entraînement : {e}")

def validate_model(model_path: str, data_path: str) -> None:
    try:
        model = YOLO(model_path)
        validation_results = model.val(data=data_path)
        print("Validation terminée. Métriques :", validation_results)
    except Exception as e:
        print(f"Erreur lors de la validation : {e}")

def predict_fire(model, frame, conf: float):
    try:
        results = model.predict(source=frame, show=False, conf=conf, stream=False)
        if results:
            print(f"Résultats de la prédiction : {results}")  # Débogage
        return results
    except Exception as e:
        print(f"Erreur lors de la prédiction : {e}")
        return None

def play_alert(alert_file: str) -> None:
    for _ in range(ALERT_REPEATS):
        try:
            print("!!! WARNING: FEU DÉTECTÉ !!!")
            playsound(alert_file)
        except Exception as e:
            print(f"Erreur lors de la lecture de l'alerte sonore : {e}")
            break

def flash_alert_image(frame, alert_image, frame_width, frame_height):
    image_copy = frame.copy()
    
    # Redimensionner l'image d'alerte pour qu'elle corresponde à la taille de la fenêtre de la webcam
    alert_img_resized = cv2.resize(alert_image, (frame_width // 4, frame_height // 4)) 
    alert_img_height, alert_img_width = alert_img_resized.shape[:2]

    image_copy[0:alert_img_height, 0:alert_img_width] = alert_img_resized  # Coin supérieur gauche
    image_copy[0:alert_img_height, frame_width-alert_img_width:frame_width] = alert_img_resized  # Coin supérieur droit
    image_copy[frame_height-alert_img_height:frame_height, 0:alert_img_width] = alert_img_resized  # Coin inférieur gauche
    image_copy[frame_height-alert_img_height:frame_height, frame_width-alert_img_width:frame_width] = alert_img_resized  # Coin inférieur droit

    return image_copy

def plot_bboxes(results, frame):
    if results:
        for result in results:
            if result.boxes is not None:
                boxes = result.boxes.cpu().numpy()
                xyxys = boxes.xyxy  # Les coordonnées des boîtes (x1, y1, x2, y2)
                confidences = boxes.conf  # Les confidences des boîtes
                print(f"Boîtes détectées : {xyxys}")  # Débogage des coordonnées des boîtes
                print(f"Confiance des boîtes : {confidences}")  # Débogage des confiances
                for xyyx, conf in zip(xyxys, confidences):
                    x1, y1, x2, y2 = map(int, xyyx)  # Décomposer les coordonnées
                    print(f"Rectangle à afficher : ({x1}, {y1}), ({x2}, {y2})")  # Vérifier les coordonnées
                    cv2.rectangle(frame, (x1, y1), (x2, y2), (255, 0, 0), 2)  # Dessiner la boîte en bleu
                    label = f"Conf: {conf:.2f}"
                    cv2.putText(frame, label, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 2)
    return frame

def detect_fire_and_alert(model, frame, conf: float, alert_played: bool) -> bool:
    print("Démarrage de la détection...")
    results = predict_fire(model, frame, conf)
    if results:
        for result in results:
            if result.boxes is not None:
                for box in result.boxes:
                    class_index = int(box.cls)
                    class_name = model.names[class_index]
                    print(f"Classe détectée : {class_name}")

                    if class_name == "fire" and not alert_played:
                        print("Feu détecté, alerte en cours.")
                        alert_thread = threading.Thread(target=play_alert, args=(ALERT_FILE,))
                        alert_thread.daemon = True
                        alert_thread.start()
                        alert_played = True

                frame = plot_bboxes(results, frame)
    return alert_played

def display_webcam(model, source, conf):
    cap = cv2.VideoCapture(source)  
    if not cap.isOpened():
        print("Erreur d'ouverture de la webcam.")
        return

    alert_played = False
    frame_count = 0
    prediction_interval = 10  # Effectuer une prédiction tous les 10 frames

    while True:
        ret, frame = cap.read()
        if not ret:
            print("Erreur de lecture de l'image")
            break

        frame_count += 1
        frame_height, frame_width = frame.shape[:2]  #

        # Effectuer une prédiction tous les prediction_interval frames
        if frame_count % prediction_interval == 0:
            alert_played = detect_fire_and_alert(model, frame, conf, alert_played)

        # Ajouter les images d'alerte si un feu a été détecté
        if alert_played:
            frame = flash_alert_image(frame, warning_img, frame_width, frame_height)

        # Afficher l'image de la webcam avec l'alerte intégrée
        cv2.imshow("Webcam avec alerte", frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

def main():
    model = YOLO(MODEL_PATH)
    display_webcam(model=model, source=0, conf=0.5)

if __name__ == "__main__":
    main()
