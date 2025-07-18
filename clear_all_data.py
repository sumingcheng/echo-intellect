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
        print("   - Milvus向量库中的所有向量")
        print("   - Meilisearch中的所有文档")
        print("")
        
        confirm = input("🤔 确定要继续吗？输入 'YES' 确认: ")
        if confirm != "YES":
            print("❌ 操作已取消")
            return False
        
        print("\n🗑️  开始清空数据...")
        
        # 1. 清空MongoDB
        logger.info("1️⃣ 清空MongoDB数据...")
        success_mongo = await clear_mongodb()
        
        # 2. 清空Milvus
        logger.info("2️⃣ 清空Milvus向量库...")
        success_milvus = await clear_milvus()
        
        # 3. 清空Meilisearch
        logger.info("3️⃣ 清空Meilisearch索引...")
        success_meili = await clear_meilisearch()
        
        if success_mongo and success_milvus and success_meili:
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
        from app.vectorstores.mongo_metadata import mongo_store
        
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

async def clear_milvus():
    """清空Milvus向量库"""
    try:
        from app.vectorstores.milvus_store import milvus_store
        
        # 连接Milvus
        milvus_store.connect(dimension=1024)
        
        if milvus_store.collection:
            # 获取向量数量
            stats = milvus_store.collection.num_entities
            logger.info(f"📊 Milvus集合 '{milvus_store.collection_name}': {stats} 个向量")
            
            if stats > 0:
                # 删除所有数据
                expr = "id >= 0"  # 删除所有记录
                milvus_store.collection.delete(expr)
                
                # 重新加载集合以确保删除生效
                milvus_store.collection.load()
                
                # 验证删除结果
                new_stats = milvus_store.collection.num_entities
                logger.info(f"🗑️  删除后向量数量: {new_stats}")
                
                if new_stats == 0:
                    logger.info("✅ Milvus向量库清空成功")
                else:
                    logger.warning(f"⚠️ Milvus可能未完全清空，剩余: {new_stats}")
            else:
                logger.info("✅ Milvus向量库已经为空")
        else:
            logger.info("✅ Milvus集合不存在或未初始化")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Milvus清空失败: {e}")
        return False

async def clear_meilisearch():
    """清空Meilisearch索引"""
    try:
        import meilisearch
        from config.settings import app_config
        
        # 连接Meilisearch
        client = meilisearch.Client(
            url=app_config.meilisearch_url,
            api_key=app_config.meilisearch_api_key
        )
        
        index_name = "rag_documents"
        
        try:
            # 获取索引
            index = client.index(index_name)
            
            # 获取文档数量
            stats = index.get_stats()
            doc_count = stats.get('numberOfDocuments', 0)
            logger.info(f"📊 Meilisearch索引 '{index_name}': {doc_count} 个文档")
            
            if doc_count > 0:
                # 删除所有文档
                task = index.delete_all_documents()
                logger.info(f"🗑️  删除任务ID: {task.task_uid}")
                
                # 等待任务完成
                client.wait_for_task(task.task_uid)
                
                # 验证删除结果
                new_stats = index.get_stats()
                new_count = new_stats.get('numberOfDocuments', 0)
                logger.info(f"🗑️  删除后文档数量: {new_count}")
                
                if new_count == 0:
                    logger.info("✅ Meilisearch索引清空成功")
                else:
                    logger.warning(f"⚠️ Meilisearch可能未完全清空，剩余: {new_count}")
            else:
                logger.info("✅ Meilisearch索引已经为空")
                
        except meilisearch.errors.MeilisearchApiError as e:
            if "index_not_found" in str(e):
                logger.info("✅ Meilisearch索引不存在，无需清空")
            else:
                raise e
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Meilisearch清空失败: {e}")
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