#This file looks for new folders inside user uploads and converts them to reel if they are not already converted
import os,time
from text_to_audio import text_to_speech_file

def text_to_audio(folder):
    # print("TTA->",folder)
    with open(f"user_uploads/{folder}/desc.text") as f:
        text = f.read()
    # text_to_speech_file(text,folder)
def create_reel(folder):
    print("CR->",folder)

if __name__=="__main__":
    while True:
        with open("done.txt","r") as f:
            done_folders=f.readlines()
        done_folders=[f.strip() for f in done_folders]
        folders=os.listdir("user_uploads")

        
        for folder in folders:
            if folder not in done_folders:
                text_to_audio(folder)#Generate audio
                create_reel(folder) #Convert into reel
                with open("done.txt","a") as f:
                    f.write(folder+"\n")
        time.sleep(5)