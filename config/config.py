import os


class Config:
    MINIO_URL = os.getenv('MINIO_BASE_URL', '172.22.221.120:9000')
    MINIO_ACCESS_KEY = os.getenv('MINIO_ACCESS_KEY', 'IoeOmDzCZOkM0CiF6IK3')
    MINIO_SECRET_KEY = os.getenv('MINIO_SECRET_KEY', 'c5gKEUpeU1oirwTOmkbLtXKl0fiDCrtlkmEU0fIt')
    MINIO_BUCKET = os.getenv('MINIO_BUCKET_NAME', 'files')

    required_vars = ['MINIO_ACCESS_KEY', 'MINIO_SECRET_KEY']
    for var in required_vars:
        if locals()[var] is None:
            raise ValueError(f"环境变量 {var} 未设置。")

    @classmethod
    def as_dict(cls):
        # 敏感的配置项名称
        sensitive_keys = {'MINIO_ACCESS_KEY', 'MINIO_SECRET_KEY'}
        return {
            k: v for k, v in cls.__dict__.items()
            if not k.startswith('__') and not callable(v) and k not in sensitive_keys
        }
