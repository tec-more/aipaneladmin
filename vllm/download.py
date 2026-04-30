from huggingface_hub import hf_hub_download
import os

# 必须用国内镜像！否则必断
os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"

print("开始强制断点续传 Qwen3.6-35B...")

try:
    hf_hub_download(
        repo_id="unsloth/Qwen3.6-35B-A3B-GGUF",
        filename="Qwen3.6-35B-A3B-UD-Q4_K_XL.gguf",
        local_dir="./models",
        local_dir_use_symlinks=False,
        resume_download=True,    # 强制开启断点续传
        force_download=False,    # 不重新下，只续传
    )
    print("✅ 续传完成！真的下完了！")

except Exception as e:
    print("❌ 续传失败，继续重试！")
    print("错误：", e)