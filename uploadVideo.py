import datetime
import os

from database_tool.video_load_tool import get_screen_orientation, add_video_record, ftp_upload, delete_video_record
from ffmpeg_tool.subtitles_audio_tool import get_video_length
# from ffmpeg_tool.video_load_tool import get_screen_orientation, add_video_record, ftp_upload, delete_video_record

upload_video_path = input('请输入视频文件夹位置：')

upload_location = input('请输入上传视频内容所属地方：')

cate_str = input('所属类别')

# 计算视频数量
num = 0

if os.path.exists(upload_video_path):
    video_files = []
    for root, dirs, files in os.walk(upload_video_path):
        for file in files:
            if file.lower().endswith(('.mp4', '.avi', '.mov', '.mkv', '.flv')):
                video_files.append(os.path.join(root, file))

    # 在界面上显示找到的视频文件数量
    print(f"文件中存在{len(video_files)}个视频")
    for i, file in enumerate(video_files):
        # 提取文件名（去掉路径）
        file_text = os.path.splitext(os.path.basename(file))[0]
        file_tag_list = file_text.split('_')

        # 不符合格式
        if len(file_tag_list) < 1:
            continue

        video_title = file_tag_list[0]
        video_tags = '_'.join(file_tag_list)
        video_param = {
            'title': video_title,
            'firstTags': video_tags,
            'secondTags': upload_location,
            'screen': get_screen_orientation(file),
            'cate': cate_str
        }

        if video_param['screen'] == -1:
            print(file + '不是1080p,跳过')
            continue

        if os.path.exists(file):
            # 上传创建时间
            created_date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            # 视频时长
            video_length = str(get_video_length(file))
            video_param['createdDate'] = created_date
            video_param['videoLength'] = video_length
            try:
                video_id = add_video_record(video_param)
                if not video_id:
                    raise Exception
            except Exception as e:
                print(f'第{i + 1}个数据写入信息失败{e}，可能是标题重复请修改标题')
                continue
            try:
                ftp_upload(video_id, file)
                num += 1
                print(f'成功上传一个视频:' + video_param['title'] + f'已上传{num}个视频')
            except Exception as e:
                print(f'第{i + 1}个上传视频失败{e}')
                delete_video_record(video_id)
                continue
        print(f"文件中存在{len(video_files)}个视频，已上传{num}个")
