import gradio as gr
import argparse
import gdown
import cv2
import numpy as np
import os
import sys
sys.path.append(sys.path[0]+"/tracker")
sys.path.append(sys.path[0]+"/tracker/model")
from track_anything import TrackingAnything
from track_anything import parse_augment
import requests
import json
import torchvision
import torch 
from tools.painter import mask_painter
import psutil
import time
try: 
    from mmcv.cnn import ConvModule
except:
    os.system("mim install mmcv")

# download checkpoints
def download_checkpoint(url, folder, filename):
    os.makedirs(folder, exist_ok=True)
    filepath = os.path.join(folder, filename)

    if not os.path.exists(filepath):
        print("download checkpoints ......")
        response = requests.get(url, stream=True)
        with open(filepath, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)

        print("download successfully!")

    return filepath
    def save_mask(mask, video_state):
        video_state["masks"][video_state["select_frame_number"]] = mask
        video_state["logits"][video_state["select_frame_number"]] = None
        painted_image = mask_painter(video_state["origin_images"][video_state["select_frame_number"]], mask)
        video_state["painted_images"][video_state["select_frame_number"]] = painted_image

    def track_anything(video_input, click_input):
        # ... existing code ...
        interface = gr.Interface(fn=track_anything, inputs=[video_input, click_input], outputs=output, title=title, description=description, theme=theme, layout=layout)
        interface.add_button("Save Mask", save_mask, video_state)
        interface.launch()

def download_checkpoint_from_google_drive(file_id, folder, filename):
    os.makedirs(folder, exist_ok=True)
    filepath = os.path.join(folder, filename)

    if not os.path.exists(filepath):
        print("Downloading checkpoints from Google Drive... tips: If you cannot see the progress bar, please try to download it manuall \
              and put it in the checkpointes directory. E2FGVI-HQ-CVPR22.pth: https://github.com/MCG-NKU/E2FGVI(E2FGVI-HQ model)")
        url = f"https://drive.google.com/uc?id={file_id}"
        gdown.download(url, filepath, quiet=False)
        print("Downloaded successfully!")

    return filepath

# convert points input to prompt state
def get_prompt(click_state, click_input):
    inputs = json.loads(click_input)
    points = click_state[0]
    labels = click_state[1]
    for input in inputs:
        points.append(input[:2])
        labels.append(input[2])
    click_state[0] = points
    click_state[1] = labels
    prompt = {
        "prompt_type":["click"],
        "input_point":click_state[0],
        "input_label":click_state[1],
        "multimask_output":"True",
    }
    return prompt


# extract frames from selected image folder
def get_frames_from_folder(folder_path, fps=30):
    """
    Args:
        folder_path:str
    Return 
        video_state, video_info, video_state["origin_images"][0], gr.update(visible=True, maximum=len(frames), value=1), gr.update(visible=True, maximum=len(frames), value=len(frames)), \
                        gr.update(visible=True),\
                        gr.update(visible=True), gr.update(visible=True), \
                        gr.update(visible=True), gr.update(visible=True), \
                        gr.update(visible=True), gr.update(visible=True), \
                        gr.update(visible=True), gr.update(visible=True), \
                        gr.update(visible=True), \
                        gr.update(visible=True, value=operation_log)
    """
    frames = []
    user_name = time.time()
    operation_log = [("",""),("Read images from folder already. Try click the image for adding targets to track and inpaint.","Normal")]
    try:
        for filename in os.listdir(folder_path):
            if filename.endswith(".png"):
                frame = cv2.imread(os.path.join(folder_path, filename))
                frames.append(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
    except (OSError, TypeError, ValueError, KeyError, SyntaxError) as e:
        print("read_frame_source:{} error. {}\n".format(folder_path, str(e)))
    image_size = (frames[0].shape[0],frames[0].shape[1]) 
    # initialize video_state
    video_state = {
        "user_name": user_name,
        "video_name": os.path.split(folder_path)[-1],
        "origin_images": frames,
        "painted_images": frames.copy(),
        "masks": [np.zeros((frames[0].shape[0],frames[0].shape[1]), np.uint8)]*len(frames),
        "logits": [None]*len(frames),
        "select_frame_number": 0,
        "fps": fps
        }
    video_info = "Video Name: {}, FPS: {}, Total Frames: {}, Image Size:{}".format(video_state["video_name"], video_state["fps"], len(frames), image_size)
    model.samcontroler.sam_controler.reset_image() 
    model.samcontroler.sam_controler.set_image(video_state["origin_images"][0])
    return video_state, video_info, video_state["origin_images"][0], gr.update(visible=True, maximum=len(frames), value=1), gr.update(visible=True, maximum=len(frames), value=len(frames)), \
                        gr.update(visible=True),\
                        gr.update(visible=True), gr.update(visible=True), \
                        gr.update(visible=True), gr.update(visible=True), \
                        gr.update(visible=True), gr.update(visible=True), \
                        gr.update(visible=True), gr.update(visible=True), \
                        gr.update(visible=True), \
                        gr.update(visible=True, value=operation_log)
                        
# extract frames from upload video
def get_frames_from_video(video_input, video_state):
    """
    Args:
        video_path:str
        timestamp:float64
    Return 
        [[0:nearest_frame], [nearest_frame:], nearest_frame]
    """
    video_path = video_input
    frames = []
    user_name = time.time()
    operation_log = [("",""),("Upload video already. Try click the image for adding targets to track and inpaint.","Normal")]
    try:
        cap = cv2.VideoCapture(video_path)
        fps = cap.get(cv2.CAP_PROP_FPS)
        while cap.isOpened():
            ret, frame = cap.read()
            if ret == True:
                current_memory_usage = psutil.virtual_memory().percent
                frames.append(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
                if current_memory_usage > 90:
                    operation_log = [("Memory usage is too high (>90%). Stop the video extraction. Please reduce the video resolution or frame rate.", "Error")]
                    print("Memory usage is too high (>90%). Please reduce the video resolution or frame rate.")
                    break
            else:
                break
    except (OSError, TypeError, ValueError, KeyError, SyntaxError) as e:
        print("read_frame_source:{} error. {}\n".format(video_path, str(e)))
    image_size = (frames[0].shape[0],frames[0].shape[1]) 
    # initialize video_state
    video_state = {
        "user_name": user_name,
        "video_name": os.path.split(video_path)[-1],
        "origin_images": frames,
        "painted_images": frames.copy(),
        "masks": [np.zeros((frames[0].shape[0],frames[0].shape[1]), np.uint8)]*len(frames),
        "logits": [None]*len(frames),
        "select_frame_number": 0,
        "fps": fps
        }
    video_info = "Video Name: {}, FPS: {}, Total Frames: {}, Image Size:{}".format(video_state["video_name"], video_state["fps"], len(frames), image_size)
    model.samcontroler.sam_controler.reset_image() 
    model.samcontroler.sam_controler.set_image(video_state["origin_images"][0])
    return video_state, video_info, video_state["origin_images"][0], gr.update(visible=True, maximum=len(frames), value=1), gr.update(visible=True, maximum=len(frames), value=len(frames)), \
                        gr.update(visible=True),\
                        gr.update(visible=True), gr.update(visible=True), \
                        gr.update(visible=True), gr.update(visible=True), \
                        gr.update(visible=True), gr.update(visible=True), \
                        gr.update(visible=True), gr.update(visible=True), \
                        gr.update(visible=True), \
                        gr.update(visible=True, value=operation_log)

def get_frames_from_video2(video_input, folder_input, video_state):
    user_name = time.time()
    frames = []
    frame_names = []
    print("video_input: {}".format(video_input))
    print("folder_input: {}".format(folder_input))
    if video_input is not None and os.path.exists(video_input):
        # 从视频文件中提取帧
        operation_log = [("",""),("Upload video already. Try click the image for adding targets to track and inpaint.","Normal")]
        cap = cv2.VideoCapture(video_input)
        i = 0
        while cap.isOpened():
            ret, frame = cap.read()
            if ret:
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                frames.append(frame)
                frame_names.append("{:05d}".format(i))
            else:
                break
            i+=1
        cap.release()
        video_info = f"Extracted {len(frames)} frames from video."
        input_name = os.path.split(video_path)[-1]
        fps = video_input['fps']
    elif folder_input is not None and os.path.exists(folder_input):
        operation_log = [("",""),("Upload img folder already. Try click the image for adding targets to track and inpaint.","Normal")]
        # 从文件夹中读取图片作为帧
        i = 0
        for filename in sorted(os.listdir(folder_input)):
            if filename.lower().endswith(('.png', '.jpg', '.jpeg')):
                img_path = os.path.join(folder_input, filename)
                img = cv2.imread(img_path)
                img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                frames.append(img)
                frame_names.append("{:05d}".format(i))
                i+=1
        video_info = f"Loaded {len(frames)} images from folder."
        input_name = folder_input.replace("/", "_").replace("\\", "_")+".mp4"
        fps = 30
    else:
        return video_state, "No valid video or folder path provided."
    image_size = (frames[0].shape[0],frames[0].shape[1]) 
    # initialize video_state
    video_state = {
        "user_name": user_name,
        "video_name": input_name,
        "origin_images": frames,
        "origin_image_names": frame_names,
        "painted_images": frames.copy(),
        "masks": [np.zeros((frames[0].shape[0],frames[0].shape[1]), np.uint8)]*len(frames),
        "logits": [None]*len(frames),
        "select_frame_number": 0,
        "fps": fps
        }
    model.samcontroler.sam_controler.reset_image() 
    model.samcontroler.sam_controler.set_image(video_state["origin_images"][0])
    return video_state, video_info, video_state["origin_images"][0], gr.update(visible=True, maximum=len(frames), value=1), gr.update(visible=True, maximum=len(frames), value=len(frames)), \
                        gr.update(visible=True),\
                        gr.update(visible=True), gr.update(visible=True), \
                        gr.update(visible=True), gr.update(visible=True), \
                        gr.update(visible=True), gr.update(visible=True), \
                        gr.update(visible=True), gr.update(visible=True), \
                        gr.update(visible=True), \
                        gr.update(visible=True, value=operation_log)

def run_example(example):
    return video_input
# get the select frame from gradio slider
def select_template(image_selection_slider, video_state, interactive_state, mask_dropdown):

    # images = video_state[1]
    image_selection_slider -= 1
    video_state["select_frame_number"] = image_selection_slider

    # once select a new template frame, set the image in sam

    model.samcontroler.sam_controler.reset_image()
    model.samcontroler.sam_controler.set_image(video_state["origin_images"][image_selection_slider])

    # update the masks when select a new template frame
    # if video_state["masks"][image_selection_slider] is not None:
        # video_state["painted_images"][image_selection_slider] = mask_painter(video_state["origin_images"][image_selection_slider], video_state["masks"][image_selection_slider])
    if mask_dropdown:
        print("ok")
    operation_log = [("",""), ("Select frame {}. Try click image and add mask for tracking.".format(image_selection_slider),"Normal")]


    return video_state["painted_images"][image_selection_slider], video_state, interactive_state, operation_log

# set the tracking end frame
def get_end_number(track_pause_number_slider, video_state, interactive_state):
    interactive_state["track_end_number"] = track_pause_number_slider
    operation_log = [("",""),("Set the tracking finish at frame {}".format(track_pause_number_slider),"Normal")]

    return video_state["painted_images"][track_pause_number_slider],interactive_state, operation_log

def get_resize_ratio(resize_ratio_slider, interactive_state):
    interactive_state["resize_ratio"] = resize_ratio_slider

    return interactive_state

# use sam to get the mask
def sam_refine(video_state, point_prompt, click_state, interactive_state, evt:gr.SelectData):
    """
    Args:
        template_frame: PIL.Image
        point_prompt: flag for positive or negative button click
        click_state: [[points], [labels]]
    """
    if point_prompt == "Positive":
        coordinate = "[[{},{},1]]".format(evt.index[0], evt.index[1])
        interactive_state["positive_click_times"] += 1
    else:
        coordinate = "[[{},{},0]]".format(evt.index[0], evt.index[1])
        interactive_state["negative_click_times"] += 1
    
    # prompt for sam model
    model.samcontroler.sam_controler.reset_image()
    model.samcontroler.sam_controler.set_image(video_state["origin_images"][video_state["select_frame_number"]])
    prompt = get_prompt(click_state=click_state, click_input=coordinate)

    mask, logit, painted_image = model.first_frame_click( 
                                                      image=video_state["origin_images"][video_state["select_frame_number"]], 
                                                      points=np.array(prompt["input_point"]),
                                                      labels=np.array(prompt["input_label"]),
                                                      multimask=prompt["multimask_output"],
                                                      )
    video_state["masks"][video_state["select_frame_number"]] = mask
    video_state["logits"][video_state["select_frame_number"]] = logit
    video_state["painted_images"][video_state["select_frame_number"]] = painted_image

    operation_log = [("",""), ("Use SAM for segment. You can try add positive and negative points by clicking. Or press Clear clicks button to refresh the image. Press Add mask button when you are satisfied with the segment","Normal")]
    return painted_image, video_state, interactive_state, operation_log

def add_multi_mask(video_state, interactive_state, mask_dropdown):
    try:
        mask = video_state["masks"][video_state["select_frame_number"]]
        interactive_state["multi_mask"]["masks"].append(mask)
        interactive_state["multi_mask"]["mask_names"].append("mask_{:03d}".format(len(interactive_state["multi_mask"]["masks"])))
        mask_dropdown.append("mask_{:03d}".format(len(interactive_state["multi_mask"]["masks"])))
        select_frame, run_status = show_mask(video_state, interactive_state, mask_dropdown)

        operation_log = [("",""),("Added a mask, use the mask select for target tracking or inpainting.","Normal")]
    except:
        operation_log = [("Please click the left image to generate mask.", "Error"), ("","")]
    return interactive_state, gr.update(choices=interactive_state["multi_mask"]["mask_names"], value=mask_dropdown), select_frame, [[],[]], operation_log

def clear_click(video_state, click_state):
    click_state = [[],[]]
    template_frame = video_state["origin_images"][video_state["select_frame_number"]]
    operation_log = [("",""), ("Clear points history and refresh the image.","Normal")]
    return template_frame, click_state, operation_log

def remove_multi_mask(interactive_state, mask_dropdown):
    interactive_state["multi_mask"]["mask_names"]= []
    interactive_state["multi_mask"]["masks"] = []

    operation_log = [("",""), ("Remove all mask, please add new masks","Normal")]
    return interactive_state, gr.update(choices=[],value=[]), operation_log

def show_mask(video_state, interactive_state, mask_dropdown):
    mask_dropdown.sort()
    select_frame = video_state["origin_images"][video_state["select_frame_number"]]
    for i in range(len(mask_dropdown)):
        mask_number = int(mask_dropdown[i].split("_")[1]) - 1
        mask = interactive_state["multi_mask"]["masks"][mask_number]
        select_frame = mask_painter(select_frame, mask.astype('uint8'), mask_color=mask_number+2)
    
    operation_log = [("",""), ("Select {} for tracking or inpainting".format(mask_dropdown),"Normal")]
    return select_frame, operation_log

# tracking vos
def vos_tracking_video(video_state, interactive_state, mask_dropdown):
    operation_log = [("",""), ("Track the selected masks, and then you can select the masks for inpainting.","Normal")]
    model.xmem.clear_memory()
    if interactive_state["track_end_number"]:
        following_frames = video_state["origin_images"][video_state["select_frame_number"]:interactive_state["track_end_number"]]
    else:
        following_frames = video_state["origin_images"][video_state["select_frame_number"]:]

    if interactive_state["multi_mask"]["masks"]:
        if len(mask_dropdown) == 0:
            mask_dropdown = ["mask_001"]
        mask_dropdown.sort()
        template_mask = interactive_state["multi_mask"]["masks"][int(mask_dropdown[0].split("_")[1]) - 1] * (int(mask_dropdown[0].split("_")[1]))
        for i in range(1,len(mask_dropdown)):
            mask_number = int(mask_dropdown[i].split("_")[1]) - 1 
            template_mask = np.clip(template_mask+interactive_state["multi_mask"]["masks"][mask_number]*(mask_number+1), 0, mask_number+1)
        video_state["masks"][video_state["select_frame_number"]]= template_mask
    else:      
        template_mask = video_state["masks"][video_state["select_frame_number"]]
    fps = video_state["fps"]

    # operation error
    if len(np.unique(template_mask))==1:
        template_mask[0][0]=1
        operation_log = [("Error! Please add at least one mask to track by clicking the left image.","Error"), ("","")]
        # return video_output, video_state, interactive_state, operation_error
    masks, logits, painted_images = model.generator(images=following_frames, template_mask=template_mask)
    # clear GPU memory
    model.xmem.clear_memory()

    if interactive_state["track_end_number"]: 
        video_state["masks"][video_state["select_frame_number"]:interactive_state["track_end_number"]] = masks
        video_state["logits"][video_state["select_frame_number"]:interactive_state["track_end_number"]] = logits
        video_state["painted_images"][video_state["select_frame_number"]:interactive_state["track_end_number"]] = painted_images
    else:
        video_state["masks"][video_state["select_frame_number"]:] = masks
        video_state["logits"][video_state["select_frame_number"]:] = logits
        video_state["painted_images"][video_state["select_frame_number"]:] = painted_images

    video_output = generate_video_from_frames(video_state["painted_images"], output_path="./result/track/{}".format(video_state["video_name"]), fps=fps) # import video_input to name the output video
    interactive_state["inference_times"] += 1
    
    print("For generating this tracking result, inference times: {}, click times: {}, positive: {}, negative: {}".format(interactive_state["inference_times"], 
                                                                                                                                           interactive_state["positive_click_times"]+interactive_state["negative_click_times"],
                                                                                                                                           interactive_state["positive_click_times"],
                                                                                                                                        interactive_state["negative_click_times"]))

    #### shanggao code for mask save
    if interactive_state["mask_save"]:
        # report error after click MaskSave button
        if not os.path.exists('./result/mask/{}'.format(video_state["video_name"].split('.')[0])):
            os.makedirs('./result/mask/{}'.format(video_state["video_name"].split('.')[0]))
        i = 0
        print("save mask")
        for mask in video_state["masks"]:
            np.save(os.path.join('./result/mask/{}'.format(video_state["video_name"].split('.')[0]), '{:05d}.npy'.format(i)), mask)
            i+=1
        # save_mask(video_state["masks"], video_state["video_name"])
    #### shanggao code for mask save
    return video_output, video_state, interactive_state, operation_log

# extracting masks from mask_dropdown
# def extract_sole_mask(video_state, mask_dropdown):
#     combined_masks = 
#     unique_masks = np.unique(combined_masks)
#     return 0 

# inpaint 
def inpaint_video(video_state, interactive_state, mask_dropdown):
    operation_log = [("",""), ("Removed the selected masks.","Normal")]

    frames = np.asarray(video_state["origin_images"])
    fps = video_state["fps"]
    inpaint_masks = np.asarray(video_state["masks"])
    if len(mask_dropdown) == 0:
        mask_dropdown = ["mask_001"]
    mask_dropdown.sort()
    # convert mask_dropdown to mask numbers
    inpaint_mask_numbers = [int(mask_dropdown[i].split("_")[1]) for i in range(len(mask_dropdown))]
    # interate through all masks and remove the masks that are not in mask_dropdown
    unique_masks = np.unique(inpaint_masks)
    num_masks = len(unique_masks) - 1
    for i in range(1, num_masks + 1):
        if i in inpaint_mask_numbers:
            continue
        inpaint_masks[inpaint_masks==i] = 0
    # inpaint for videos

    try:
        inpainted_frames = model.baseinpainter.inpaint(frames, inpaint_masks, ratio=interactive_state["resize_ratio"])   # numpy array, T, H, W, 3
    except:
        operation_log = [("Error! You are trying to inpaint without masks input. Please track the selected mask first, and then press inpaint. If VRAM exceeded, please use the resize ratio to scaling down the image size.","Error"), ("","")]
        inpainted_frames = video_state["origin_images"]
    video_output = generate_video_from_frames(inpainted_frames, output_path="./result/inpaint/{}".format(video_state["video_name"]), fps=fps) # import video_input to name the output video

    return video_output, operation_log


# generate video after vos inference
def generate_video_from_frames(frames, output_path, fps=30):
    """
    Generates a video from a list of frames.
    
    Args:
        frames (list of numpy arrays): The frames to include in the video.
        output_path (str): The path to save the generated video.
        fps (int, optional): The frame rate of the output video. Defaults to 30.
    """
    # height, width, layers = frames[0].shape
    # fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    # video = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
    # print(output_path)
    # for frame in frames:
    #     video.write(frame)
    
    # video.release()
    frames = torch.from_numpy(np.asarray(frames))
    if not os.path.exists(os.path.dirname(output_path)):
        os.makedirs(os.path.dirname(output_path))
    torchvision.io.write_video(output_path, frames, fps=fps, video_codec="libx264")
    return output_path

def mask_save_frome_video(video_state, interactive_state, mask_dropdown, save_path):
    if not save_path:
        save_path = './result/mask/'
    final_save_path = os.path.join(save_path, video_state["video_name"].split('.')[0])
    operation_log = [("",""), ("save mask to {}".format(final_save_path), "Normal")]
    
    if video_state["video_name"] == '':
        operation_log = [("Error! need tracking video first","Error"), ("","")]
    
    if not os.path.exists(final_save_path):
        os.makedirs(final_save_path)
    print("save mask to {}/xx.png.".format(final_save_path))
    try:
        # for mask in video_state["masks"]:
        for i in range(len(video_state["masks"])):
            mask = video_state["masks"][i]    
            # interactive_state["multi_mask"]["masks"]
            save_mask_i_path = os.path.join(final_save_path, '{}.png'.format(video_state['origin_image_names'][i]))
            print("save mask: {}".format(save_mask_i_path))
            cv2.imwrite(save_mask_i_path, mask)
    except:
        operation_log = [("Error! Something wrong when saving mask image to: {}".format(final_save_path),"Error"), ("","")]
    return operation_log

# args, defined in track_anything.py
args = parse_augment()

# check and download checkpoints if needed
SAM_checkpoint_dict = {
    'vit_h': "sam_vit_h_4b8939.pth",
    'vit_l': "sam_vit_l_0b3195.pth", 
    "vit_b": "sam_vit_b_01ec64.pth"
}
SAM_checkpoint_url_dict = {
    'vit_h': "https://dl.fbaipublicfiles.com/segment_anything/sam_vit_h_4b8939.pth",
    'vit_l': "https://dl.fbaipublicfiles.com/segment_anything/sam_vit_l_0b3195.pth",
    'vit_b': "https://dl.fbaipublicfiles.com/segment_anything/sam_vit_b_01ec64.pth"
}
sam_checkpoint = SAM_checkpoint_dict[args.sam_model_type] 
sam_checkpoint_url = SAM_checkpoint_url_dict[args.sam_model_type] 
xmem_checkpoint = "XMem-s012.pth"
xmem_checkpoint_url = "https://github.com/hkchengrex/XMem/releases/download/v1.0/XMem-s012.pth"
e2fgvi_checkpoint = "E2FGVI-HQ-CVPR22.pth"
e2fgvi_checkpoint_id = "10wGdKSUOie0XmCr8SQ2A2FeDe-mfn5w3"


folder ="./checkpoints"
SAM_checkpoint = download_checkpoint(sam_checkpoint_url, folder, sam_checkpoint)
xmem_checkpoint = download_checkpoint(xmem_checkpoint_url, folder, xmem_checkpoint)
e2fgvi_checkpoint = download_checkpoint_from_google_drive(e2fgvi_checkpoint_id, folder, e2fgvi_checkpoint)
args.port = 12211
# args.device = "cuda:3"
# args.mask_save = True

# initialize sam, xmem, e2fgvi models
model = TrackingAnything(SAM_checkpoint, xmem_checkpoint, e2fgvi_checkpoint,args)


title = """<p><h1 align="center">Track-Anything</h1></p>
    """
description = """<p>Gradio demo for Track Anything, a flexible and interactive tool for video object tracking, segmentation, and inpainting. I To use it, simply upload your video, or click one of the examples to load them. Code: <a href="https://github.com/gaomingqi/Track-Anything">https://github.com/gaomingqi/Track-Anything</a> <a href="https://huggingface.co/spaces/watchtowerss/Track-Anything?duplicate=true"><img style="display: inline; margin-top: 0em; margin-bottom: 0em" src="https://bit.ly/3gLdBN6" alt="Duplicate Space" /></a></p>"""

# 在Tracking, Inpainting这两个button的右侧添加一个MaskSave按钮，与interactive_state【'mask_save']绑定，用于保存mask
with gr.Blocks() as iface:
    """
        state for 
    """
    click_state = gr.State([[],[]])
    interactive_state = gr.State({
        "inference_times": 0,
        "negative_click_times" : 0,
        "positive_click_times": 0,
        "mask_save": args.mask_save,
        "multi_mask": {
            "mask_names": [],
            "masks": []
        },
        "track_end_number": None,
        "resize_ratio": 1
    }
    )

    video_state = gr.State(
        {
        "user_name": "",
        "video_name": "",
        "origin_images": None,
        "painted_images": None,
        "masks": None,
        "inpaint_masks": None,
        "logits": None,
        "select_frame_number": 0,
        "fps": 30
        }
    )
    gr.Markdown(title)
    gr.Markdown(description)
    with gr.Row():

        # for user video input
        with gr.Column():
            with gr.Row(scale=0.4):
                video_input = gr.Video(autosize=True)
                
                    
                with gr.Column():
                    video_info = gr.Textbox(label="Video Info")
                    # 新增函数：从给定文件夹路径读取所有图片
                    folder_input = gr.Textbox(label="Enter folder path")
                    save_path_input = gr.Textbox(label="Enter path to save masks", value="./result/mask/")
                    
                    resize_info = gr.Textbox(value="If you want to use the inpaint function, it is best to git clone the repo and use a machine with more VRAM locally. \
                                            Alternatively, you can use the resize ratio slider to scale down the original image to around 360P resolution for faster processing.", label="Tips for running this demo.")
                    resize_ratio_slider = gr.Slider(minimum=0.02, maximum=1, step=0.02, value=1, label="Resize ratio", visible=True)
                    
                    image_folder_input = gr.inputs.Textbox(lines=2, placeholder="input folder path"), 
          

            with gr.Row():
                # put the template frame under the radio button
                with gr.Column():
                    # extract frames
                    with gr.Column():
                        extract_frames_button = gr.Button(value="Get video info", interactive=True, variant="primary") 
                        extract_frames_by_folder_button  = gr.Button(value="Get video info By Image Folder", interactive=True, variant="primary") 

                     # click points settins, negative or positive, mode continuous or single
                    with gr.Row():
                        with gr.Row():
                            point_prompt = gr.Radio(
                                choices=["Positive",  "Negative"],
                                value="Positive",
                                label="Point prompt",
                                interactive=True,
                                visible=False)
                            remove_mask_button = gr.Button(value="Remove mask", interactive=True, visible=False) 
                            clear_button_click = gr.Button(value="Clear clicks", interactive=True, visible=False).style(height=160)
                            Add_mask_button = gr.Button(value="Add mask", interactive=True, visible=False)
                    template_frame = gr.Image(type="pil",interactive=True, elem_id="template_frame", visible=False).style(height=360)
                    image_selection_slider = gr.Slider(minimum=1, maximum=100, step=1, value=1, label="Track start frame", visible=False)
                    track_pause_number_slider = gr.Slider(minimum=1, maximum=100, step=1, value=1, label="Track end frame", visible=False)
            
                with gr.Column():
                    run_status = gr.HighlightedText(value=[("Text","Error"),("to be","Label 2"),("highlighted","Label 3")], visible=False)
                    mask_dropdown = gr.Dropdown(multiselect=True, value=[], label="Mask selection", info=".", visible=False)
                    video_output = gr.Video(autosize=True, visible=False).style(height=360)
                    with gr.Row():
                        tracking_video_predict_button = gr.Button(value="Tracking", visible=False)
                        inpaint_video_predict_button = gr.Button(value="Inpainting", visible=False)
                        mask_save_button = gr.Button(value="MaskSave", visible=False)

    # first step: get the video information 
    extract_frames_button.click(
        fn=get_frames_from_video2,
        inputs=[
            video_input, folder_input, video_state
        ],
        outputs=[video_state, video_info, template_frame,
                 image_selection_slider, track_pause_number_slider,point_prompt, clear_button_click, Add_mask_button, template_frame,
                 tracking_video_predict_button, video_output, mask_dropdown, remove_mask_button, inpaint_video_predict_button, mask_save_button, run_status]
    )   
    
    extract_frames_by_folder_button.click(
        fn=get_frames_from_video,
        inputs=[
            image_folder_input, video_state
        ],
        outputs=[video_state, video_info, template_frame,
                 image_selection_slider, track_pause_number_slider,point_prompt, clear_button_click, Add_mask_button, template_frame,
                 tracking_video_predict_button, video_output, mask_dropdown, remove_mask_button, inpaint_video_predict_button, mask_save_button, run_status]
    )  

    # second step: select images from slider
    image_selection_slider.release(fn=select_template, 
                                   inputs=[image_selection_slider, video_state, interactive_state], 
                                   outputs=[template_frame, video_state, interactive_state, run_status], api_name="select_image")
    track_pause_number_slider.release(fn=get_end_number, 
                                   inputs=[track_pause_number_slider, video_state, interactive_state], 
                                   outputs=[template_frame, interactive_state, run_status], api_name="end_image")
    resize_ratio_slider.release(fn=get_resize_ratio, 
                                   inputs=[resize_ratio_slider, interactive_state], 
                                   outputs=[interactive_state], api_name="resize_ratio")
    
    # click select image to get mask using sam
    template_frame.select(
        fn=sam_refine,
        inputs=[video_state, point_prompt, click_state, interactive_state],
        outputs=[template_frame, video_state, interactive_state, run_status]
    )

    # add different mask
    Add_mask_button.click(
        fn=add_multi_mask,
        inputs=[video_state, interactive_state, mask_dropdown],
        outputs=[interactive_state, mask_dropdown, template_frame, click_state, run_status]
    )

    remove_mask_button.click(
        fn=remove_multi_mask,
        inputs=[interactive_state, mask_dropdown],
        outputs=[interactive_state, mask_dropdown, run_status]
    )

    # tracking video from select image and mask
    tracking_video_predict_button.click(
        fn=vos_tracking_video,
        inputs=[video_state, interactive_state, mask_dropdown],
        outputs=[video_output, video_state, interactive_state, run_status]
    )

    # inpaint video from select image and mask
    inpaint_video_predict_button.click(
        fn=inpaint_video,
        inputs=[video_state, interactive_state, mask_dropdown],
        outputs=[video_output, run_status]
    )
    
    mask_save_button.click(
        fn=mask_save_frome_video,
        inputs=[video_state, interactive_state, mask_dropdown, save_path_input],
        outputs=[run_status]
    )
    # click to get mask
    mask_dropdown.change(
        fn=show_mask,
        inputs=[video_state, interactive_state, mask_dropdown],
        outputs=[template_frame, run_status]
    )
    
    # clear input
    video_input.clear(
        lambda: (
        {
        "user_name": "",
        "video_name": "",
        "origin_images": None,
        "painted_images": None,
        "masks": None,
        "inpaint_masks": None,
        "logits": None,
        "select_frame_number": 0,
        "fps": 30
        },
        {
        "inference_times": 0,
        "negative_click_times" : 0,
        "positive_click_times": 0,
        "mask_save": args.mask_save,
        "multi_mask": {
            "mask_names": [],
            "masks": []
        },
        "track_end_number": 0,
        "resize_ratio": 1
        },
        [[],[]],
        None,
        None,
        gr.update(visible=False), gr.update(visible=False), gr.update(visible=False), \
        gr.update(visible=False), gr.update(visible=False), gr.update(visible=False), gr.update(visible=False), \
        gr.update(visible=False), gr.update(visible=False), gr.update(visible=False, value=[]), gr.update(visible=False), \
        gr.update(visible=False), gr.update(visible=False)
                        
        ),
        [],
        [ 
            video_state,
            interactive_state,
            click_state,
            video_output,
            template_frame,
            tracking_video_predict_button, image_selection_slider , track_pause_number_slider,point_prompt, clear_button_click, 
            Add_mask_button, template_frame, tracking_video_predict_button, video_output, mask_dropdown, remove_mask_button,inpaint_video_predict_button, mask_save_button, run_status
        ],
        queue=False,
        show_progress=False)

    # points clear
    clear_button_click.click(
        fn = clear_click,
        inputs = [video_state, click_state,],
        outputs = [template_frame,click_state, run_status],
    )
    # set example
    gr.Markdown("##  Examples")
    gr.Examples(
        examples=[os.path.join(os.path.dirname(__file__), "./test_sample/", test_sample) for test_sample in ["test-sample8.mp4","test-sample4.mp4", \
                                                                                                             "test-sample2.mp4","test-sample13.mp4"]],
        fn=run_example,
        inputs=[
            video_input
        ],
        outputs=[video_input],
        # cache_examples=True,
    ) 
iface.queue(concurrency_count=1)
iface.launch(debug=True, enable_queue=True, server_port=args.port, server_name="0.0.0.0")
# iface.launch(debug=True, enable_queue=True)