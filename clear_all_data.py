#!/usr/bin/env python3
"""
清空所有数据 - 向量库和MongoDB
注意：此操作不可逆，请谨慎使用！
"""

import asyncio
import logging
import sys

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger("clear-data")

async def clear_all_data():
    """清空所有数据"""
    
    try:
        # 确认操作
        print("⚠️  警告：此操作将清空所有数据！")
        print("📊 包括：")
        print("   - MongoDB中的所有datasets、collections、data")
        print("   - Qdrant向量库中的所有向量")
        print("")
        
        confirm = input("🤔 确定要继续吗？输入 'YES' 确认: ")
        if confirm != "YES":
            print("❌ 操作已取消")
            return False
        
        print("\n🗑️  开始清空数据...")
        
        # 1. 清空MongoDB
        logger.info("1️⃣ 清空MongoDB数据...")
        success_mongo = await clear_mongodb()
        
        # 2. 清空Qdrant
        logger.info("2️⃣ 清空Qdrant向量库...")
        success_qdrant = await clear_qdrant()
        
        if success_mongo and success_qdrant:
            print("\n🎉 所有数据清空完成！")
            print("💡 现在可以重新导入数据了")
            return True
        else:
            print("\n❌ 部分清空操作失败，请检查日志")
            return False
        
    except Exception as e:
        logger.error(f"❌ 清空数据失败: {e}")
        import traceback
        traceback.print_exc()
        return False

async def clear_mongodb():
    """清空MongoDB数据"""
    try:
        from app.stores.mongo import mongo_store
        
        # 连接MongoDB
        mongo_store.connect()
        
        # 获取所有集合
        collections = ['datasets', 'collections', 'data', 'conversations']
        
        total_deleted = 0
        for collection_name in collections:
            if collection_name in mongo_store._collections:
                collection = mongo_store._collections[collection_name]
                
                # 统计数据
                count_before = collection.count_documents({})
                logger.info(f"📋 {collection_name}: {count_before} 条记录")
                
                if count_before > 0:
                    # 清空集合
                    result = collection.delete_many({})
                    deleted_count = result.deleted_count
                    total_deleted += deleted_count
                    logger.info(f"🗑️  {collection_name}: 删除了 {deleted_count} 条记录")
                else:
                    logger.info(f"✅ {collection_name}: 已经为空")
        
        logger.info(f"✅ MongoDB清空完成，总共删除 {total_deleted} 条记录")
        return True
        
    except Exception as e:
        logger.error(f"❌ MongoDB清空失败: {e}")
        return False

async def clear_qdrant():
    """清空Qdrant向量库"""
    try:
        from app.stores.qdrant import qdrant_store
        from config.settings import app_config
        
        # 连接Qdrant
        qdrant_store.connect(dimension=app_config.openai_embedding_dimension)
        
        if qdrant_store.delete_collection():
            logger.info("✅ Qdrant向量库清空成功")
        else:
            logger.warning("⚠️ Qdrant集合可能不存在或清空失败")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Qdrant清空失败: {e}")
        return False

async def main():
    """主函数"""
    logger.info("🚀 启动数据清空工具")
    
    success = await clear_all_data()
    
    if success:
        logger.info("✅ 清空操作成功完成")
        return 0
    else:
        logger.error("❌ 清空操作失败")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code) 