from imagededup.methods import CNN
import os
import shutil


def merge_duplicates(duplicates):
    """
    合并重复图像集合，避免冗余。
    :param duplicates: 字典形式的重复图像集合。
    :return: 合并后的重复图像集合列表。
    """
    sets_of_duplicates = []

    for original, dupes in duplicates.items():
        current_set = set([original] + dupes)

        for duplicate_set in sets_of_duplicates:
            if not current_set.isdisjoint(duplicate_set):
                duplicate_set.update(current_set)
                break
        else:
            sets_of_duplicates.append(current_set)

    return [list(s) for s in sets_of_duplicates if len(s) > 1]


def move_and_log_duplicates(duplicate_sets, image_dir):
    """
    将重复图像移动到各自的文件夹，并记录移动关系。
    :param duplicate_sets: 合并后的重复图像集合列表。
    :param image_dir: 图像目录路径。
    """
    for duplicate_set in duplicate_sets:
        # 使用最短文件名作为目标文件夹名
        target_dir = os.path.join(image_dir, min(duplicate_set, key=len).split('.')[0])

        # 创建目标文件夹
        os.makedirs(target_dir, exist_ok=True)

        # 记录源文件和目标文件路径
        with open(os.path.join(target_dir, 'source_relation.txt'), 'a') as f:
            for file in duplicate_set:
                src_path = os.path.abspath(os.path.join(image_dir, file))
                dest_path = os.path.abspath(os.path.join(target_dir, file))
                try:
                    shutil.move(src_path, dest_path)
                except Exception as e:
                    print(f"Error moving {file}: {e}")
                f.write(f'Source: {src_path} --> Destination: {dest_path}\n')


def keep_largest_or_longest_files(folder):
    """
    在每个文件夹中保留最大的或文件名最长的文件，删除其他文件。
    :param folder: 包含重复文件的文件夹路径。
    """
    for root, _, files in os.walk(folder):
        if not files:
            continue

        # 找到最大的或文件名最长的文件
        largest_file = max(files, key=lambda f: (os.path.getsize(os.path.join(root, f)), len(f)))
        for file in files:
            if file != largest_file:
                os.remove(os.path.join(root, file))


def move_files_to_parent(parent_dir):
    """
    将所有文件从子目录移动到父目录。
    :param parent_dir: 父目录路径。
    """
    for subdir, _, files in os.walk(parent_dir):
        for file in files:
            shutil.move(os.path.join(subdir, file), os.path.join(parent_dir, file))


if __name__ == '__main__':
    # 仅支持在 python3.8 版本运行
    # 定义图像目录路径
    image_dir_path = r'C:\Users\Pusoy\Desktop\Camera'
    cnn_encoder = CNN()

    # 使用 CNN 模型查找重复图像
    duplicates = cnn_encoder.find_duplicates(image_dir=image_dir_path, min_similarity_threshold=0.98)

    # 合并重复集合
    new_duplicates = merge_duplicates(duplicates)

    # 移动并记录重复文件
    move_and_log_duplicates(new_duplicates, image_dir_path)
    print("Duplicates have been moved and logged in their respective folders.")

    # 保留每个文件夹中最大的或文件名最长的文件
    keep_largest_or_longest_files(image_dir_path)

    # 将所有文件移动到父目录
    move_files_to_parent(image_dir_path)
    print('All files have been moved to the parent directory.')
