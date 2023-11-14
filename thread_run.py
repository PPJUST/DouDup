import os

import natsort
from PySide6.QtCore import *

import satic_function


class CompareQthread(QThread):
    signal_compare_result = Signal(list, dict)  # 发送相似组结果列表
    signal_stop = Signal()  # 发送停止信号（被终止或完成）
    signal_schedule = Signal(str, str)  # 发送进度信息（类型str，进度文本str）

    def __init__(self):
        super().__init__()
        # 设置初始变量
        self.check_folder_list = None
        self.need_image_number = None
        self.mode_ahash = None
        self.mode_phash = None
        self.mode_dhash = None
        self.mode_ssim = None
        self.stop_code = False

    def reset_var(self):
        self.check_folder_list = None
        self.need_image_number = None
        self.mode_ahash = None
        self.mode_phash = None
        self.mode_dhash = None
        self.mode_ssim = None
        self.stop_code = False

    def set_check_folder_list(self, check_folder_list):
        self.check_folder_list = check_folder_list

    def set_need_image_number(self, image_number):
        self.need_image_number = image_number

    def set_mode_ahash(self, mode_ahash):
        self.mode_ahash = mode_ahash

    def set_mode_phash(self, mode_phash):
        self.mode_phash = mode_phash

    def set_mode_dhash(self, mode_dhash):
        self.mode_dhash = mode_dhash

    def set_mode_ssim(self, mode_ssim):
        self.mode_ssim = mode_ssim

    def set_stop_code(self):
        self.stop_code = True

    def run(self):
        self.signal_schedule.emit('步骤', '1/4 检查文件夹')
        # 提取文件夹中符合要求的文件夹、压缩包
        dir_set, archive_set = satic_function.walk_dirpath(self.check_folder_list)
        # 设置对应的字典，格式为{图片文件:{源文件:..., hash值:...}...}
        image_data_dict = dict()  # 图片对应的数据字典
        origin_data_dict = dict()  # 源文件对应的数据字典

        self.signal_schedule.emit('步骤', '2/4 提取图片')
        # 解压压缩包中的指定数量图片文件，并写入字典数据
        for archivefile in archive_set:
            if self.stop_code:
                return self.signal_stop.emit()
            extract_image_list, image_count_in_archive = satic_function.extract_image_from_archive(archivefile,
                                                                                                   self.need_image_number)
            # 写入图片对应的数据字典
            for i in extract_image_list:
                if i not in image_data_dict:
                    image_data_dict[i] = dict()
                image_data_dict[i]['origin_path'] = archivefile

            # 写入源文件对应的数据字典
            if archivefile not in origin_data_dict:
                origin_data_dict[archivefile] = dict()
            origin_data_dict[archivefile]['preview'] = natsort.natsorted(list(extract_image_list))[0]
            origin_data_dict[archivefile]['filetype'] = 'archive'
            origin_data_dict[archivefile]['image_number'] = image_count_in_archive
            origin_data_dict[archivefile]['filesize'] = os.path.getsize(archivefile)
        # 获取文件夹中的指定数量图片文件，并写入字典数据
        for dirpath in dir_set:
            if self.stop_code:
                return self.signal_stop.emit()
            get_image_list, image_count_in_dir = satic_function.get_image_from_dir(dirpath, self.need_image_number)
            # 写入图片对应的数据字典
            for i in get_image_list:
                image_data_dict[i] = dict()
                image_data_dict[i]['origin_path'] = dirpath

            # 写入源文件对应的数据字典
            if dirpath not in origin_data_dict:
                origin_data_dict[dirpath] = dict()
            origin_data_dict[dirpath]['preview'] = natsort.natsorted(get_image_list)[0]
            origin_data_dict[dirpath]['filetype'] = 'folder'
            origin_data_dict[dirpath]['image_number'] = image_count_in_dir
            origin_data_dict[dirpath]['filesize'] = satic_function.get_folder_size(dirpath)

        self.signal_schedule.emit('步骤', '3/4 计算图片特征')
        # 计算图片hash值
        for image in image_data_dict:
            if self.stop_code:
                return self.signal_stop.emit()
            hash_dict = satic_function.get_image_attr(image, mode_ahash=self.mode_ahash, mode_phash=self.mode_phash,
                                                      mode_dhash=self.mode_dhash)
            image_data_dict[image].update(hash_dict)

        self.signal_schedule.emit('步骤', '4/4 对比图片特征')
        # 对比hash值，查找相似项
        similar_group_list = satic_function.compare_image(image_data_dict, mode_ahash=self.mode_ahash,
                                                          mode_phash=self.mode_phash,
                                                          mode_dhash=self.mode_dhash, mode_ssim=self.mode_ssim)

        self.signal_schedule.emit('步骤', '-/- 结束')
        self.signal_compare_result.emit(similar_group_list, origin_data_dict)
        self.signal_stop.emit()