"""
增强版 RAG 检索器：支持标准岗位画像和用户画像的向量化匹配
使用 ChromaDB 向量数据库 + SentenceTransformer 嵌入模型
"""
import pandas as pd
import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
import json
from pathlib import Path
import numpy as np


class EnhancedRAGRetriever:
    """增强版岗位 RAG 检索器"""
    
    def __init__(self, excel_path=None, personas_path=None, persist_dir="./chroma_db"):
        """
        初始化 RAG 检索器
        :param excel_path: Excel 文件路径（真实招聘岗位）
        :param personas_path: 标准岗位画像 JSON 路径
        :param persist_dir: ChromaDB 持久化目录
        """
        self.persist_dir = persist_dir
        self.model = None
        self.use_tfidf = False
        self.tfidf_vectorizer = None
        
        # 两个集合：真实岗位 + 标准岗位画像
        self.job_collection = None  # 真实招聘岗位
        self.persona_collection = None  # 标准岗位画像
        
        # TF-IDF 数据
        self.tfidf_job_documents = []
        self.tfidf_job_metadatas = []
        self.tfidf_persona_documents = []
        self.tfidf_persona_metadatas = []
        
        if excel_path or personas_path:
            self._build_index(excel_path, personas_path)
    
    def _use_tfidf_mode(self):
        """使用 TF-IDF 作为备选方案（无需联网）"""
        self.use_tfidf = True
        from sklearn.feature_extraction.text import TfidfVectorizer
        self.tfidf_vectorizer = TfidfVectorizer(
            max_features=2000, 
            stop_words=['的', '了', '等', '有', '与', '及', '和', '在', '等', '是', '一个']
        )
    
    def _build_index(self, excel_path=None, personas_path=None):
        """构建向量索引"""
        print("📚 正在构建增强版岗位向量索引...")
        
        # 初始化 SentenceTransformer 语义向量模型
        print("🚀 正在加载语义向量模型 (SentenceTransformer)...")
        try:
            # 使用支持中文的多语言模型
            self.model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
            self.use_tfidf = False
            print("✅ 模型加载成功，启用语义向量检索模式")
        except Exception as e:
            print(f"⚠️ 模型加载失败：{str(e)}，回退到 TF-IDF 关键词模式")
            self._use_tfidf_mode()
        
        # 初始化 ChromaDB（用于存储和检索向量）
        try:
            client = chromadb.PersistentClient(path=self.persist_dir)
            self.job_collection = client.get_or_create_collection(
                name="job_postings",
                metadata={"hnsw:space": "cosine"}
            )
            self.persona_collection = client.get_or_create_collection(
                name="standard_personas",
                metadata={"hnsw:space": "cosine"}
            )
            print("✅ ChromaDB 向量数据库初始化完成")
        except Exception as e:
            print(f"⚠️ ChromaDB 初始化失败：{str(e)}")
        
        # 1. 加载 Excel 真实岗位数据
        if excel_path:
            self._index_excel_jobs(excel_path)
        
        # 2. 加载标准岗位画像
        if personas_path:
            self._index_personas(personas_path)
        
        print(f"✅ 增强版 RAG 索引构建完成")
        if self.use_tfidf:
            print(f"   - 真实岗位：{len(self.tfidf_job_documents)} 个")
            print(f"   - 标准岗位画像：{len(self.tfidf_persona_documents)} 个")
        else:
            job_count = self.job_collection.count() if self.job_collection else 0
            persona_count = self.persona_collection.count() if self.persona_collection else 0
            print(f"   - 真实岗位：{job_count} 个")
            print(f"   - 标准岗位画像：{persona_count} 个")
    
    def _index_excel_jobs(self, excel_path):
        """索引 Excel 中的真实招聘岗位"""
        print("\n📊 正在索引真实招聘岗位...")
        df = pd.read_excel(excel_path)
        print(f"   加载了 {len(df)} 条招聘数据")
        
        batch_size = 100
        for i in range(0, len(df), batch_size):
            batch_df = df.iloc[i:i+batch_size]
            
            documents = []
            metadatas = []
            ids = []
            
            for idx, row in batch_df.iterrows():
                # 组合文本：岗位名称 + 岗位详情 + 公司类型 + 所属行业
                text_parts = [
                    str(row.get('岗位名称', '')),
                    str(row.get('岗位详情', '')),
                    str(row.get('公司类型', '')),
                    str(row.get('所属行业', '')),
                    str(row.get('公司规模', ''))
                ]
                text = ' '.join(filter(None, text_parts))
                
                if pd.isna(text) or text.strip() == "":
                    continue
                
                documents.append(text)
                
                metadata = {
                    'job_name': row.get('岗位名称', ''),
                    'salary': str(row.get('薪资范围', '')),
                    'company': str(row.get('公司名称', '')),
                    'industry': str(row.get('所属行业', '')),
                    'company_type': str(row.get('公司类型', '')),
                    'company_size': str(row.get('公司规模', '')),
                    'city': str(row.get('地址', '')),
                    'source': 'excel_job'
                }
                metadatas.append(metadata)
                ids.append(f"job_{idx}")
            
            if documents:
                self.tfidf_job_documents.extend(documents)
                self.tfidf_job_metadatas.extend(metadatas)
                
                # 如果要用向量模式（需要下载模型）
                if not self.use_tfidf and self.model:
                    embeddings = self.model.encode(documents).tolist()
                    self.job_collection.add(
                        embeddings=embeddings,
                        documents=documents,
                        metadatas=metadatas,
                        ids=ids
                    )
            
            print(f"   已处理 {min(i+batch_size, len(df))}/{len(df)} 条数据")
        
        # 训练 TF-IDF 模型（仅在 TF-IDF 模式下执行）
        if self.tfidf_job_documents and self.tfidf_vectorizer:
            self.tfidf_vectorizer.fit(self.tfidf_job_documents)
            print(f"   ✅ 真实岗位 TF-IDF 索引构建完成")
    
    def _index_personas(self, personas_path):
        """索引标准岗位画像"""
        print("\n📋 正在索引标准岗位画像...")
        
        with open(personas_path, 'r', encoding='utf-8') as f:
            personas = json.load(f)
        
        print(f"   加载了 {len(personas)} 个标准岗位画像")
        
        documents = []
        metadatas = []
        ids = []
        
        for job_key, job_info in personas.items():
            # 组合文本：岗位名称 + 专业技能 + 项目经历 + 教育要求
            text_parts = [
                job_key,
                job_info.get('岗位名称', ''),
                ' '.join([s['name'] for s in job_info.get('专业技能', [])]),
                job_info.get('项目经历', ''),
                job_info.get('教育要求', ''),
                job_info.get('证书要求', '')
            ]
            text = ' '.join(filter(None, text_parts))
            
            if not text.strip():
                continue
            
            documents.append(text)
            
            metadata = {
                'job_name': job_info.get('岗位名称', job_key),
                'job_key': job_key,
                'skills': ', '.join([s['name'] for s in job_info.get('专业技能', [])]),
                'education': job_info.get('教育要求', ''),
                'experience': job_info.get('经验要求', ''),
                'salary': job_info.get('平均薪资', ''),
                'source': 'standard_persona'
            }
            metadatas.append(metadata)
            ids.append(f"persona_{job_key}")
        
        if documents:
            self.tfidf_persona_documents.extend(documents)
            self.tfidf_persona_metadatas.extend(metadatas)
            
            # 如果要用向量模式
            if not self.use_tfidf and self.model:
                embeddings = self.model.encode(documents).tolist()
                self.persona_collection.add(
                    embeddings=embeddings,
                    documents=documents,
                    metadatas=metadatas,
                    ids=ids
                )
            
            print(f"   ✅ 标准岗位画像 TF-IDF 索引构建完成")
    
    def match_resume_to_jobs(self, resume_text, top_k=10, use_personas=True):
        """
        为简历匹配最合适的岗位
        :param resume_text: 简历文本
        :param top_k: 返回岗位数量
        :param use_personas: 是否同时使用标准岗位画像
        :return: 匹配的岗位列表
        """
        print(f"🔍 开始为简历匹配岗位...")
        
        all_results = []
        
        # 向量化简历文本
        if not self.use_tfidf and self.model:
            # === 语义向量检索模式 ===
            resume_embedding = self.model.encode(resume_text).tolist()
            
            # 在真实岗位中检索
            if self.job_collection and self.job_collection.count() > 0:
                results = self.job_collection.query(
                    query_embeddings=[resume_embedding],
                    n_results=top_k,
                    include=['metadatas', 'distances']
                )
                for i, (meta, dist) in enumerate(zip(results['metadatas'][0], results['distances'][0])):
                    similarity = 1.0 - dist  # ChromaDB 返回的是距离，需转为相似度
                    if similarity > 0.05:  # 降低阈值以获取更多结果
                        all_results.append({
                            'job_name': meta.get('job_name', ''),
                            'company': meta.get('company', ''),
                            'salary': meta.get('salary', ''),
                            'education': meta.get('education', ''),
                            'experience': meta.get('experience', ''),
                            'similarity': float(similarity),
                            'source': 'excel_job',
                            'match_reason': '基于语义向量相似度匹配'
                        })
            
            # 在标准岗位画像中检索
            if use_personas and self.persona_collection and self.persona_collection.count() > 0:
                results = self.persona_collection.query(
                    query_embeddings=[resume_embedding],
                    n_results=top_k // 2,
                    include=['metadatas', 'distances']
                )
                for i, (meta, dist) in enumerate(zip(results['metadatas'][0], results['distances'][0])):
                    similarity = 1.0 - dist
                    if similarity > 0.05:  # 降低阈值以获取更多结果
                        all_results.append({
                            'job_name': meta.get('job_name', ''),
                            'salary': meta.get('salary', ''),
                            'education': meta.get('education', ''),
                            'experience': meta.get('experience', ''),
                            'skills': meta.get('skills', ''),
                            'similarity': float(similarity),
                            'source': 'standard_persona',
                            'match_reason': '基于语义向量与标准画像匹配'
                        })
        else:
            # === TF-IDF 关键词匹配模式（兜底） ===
            if not self.tfidf_vectorizer:
                return []
            
            resume_vec = self.tfidf_vectorizer.transform([resume_text])
            
            # 在真实岗位中检索
            if self.tfidf_job_documents:
                job_vecs = self.tfidf_vectorizer.transform(self.tfidf_job_documents)
                job_similarities = cosine_similarity(resume_vec, job_vecs).flatten()
                
                top_job_indices = np.argsort(job_similarities)[::-1][:top_k]
                
                for idx in top_job_indices:
                    if job_similarities[idx] > 0.01:  # 降低阈值从0.05到0.01
                        meta = self.tfidf_job_metadatas[idx]
                        all_results.append({
                            'job_name': meta.get('job_name', ''),
                            'company': meta.get('company', ''),
                            'salary': meta.get('salary', ''),
                            'education': meta.get('education', ''),
                            'experience': meta.get('experience', ''),
                            'similarity': float(job_similarities[idx]),
                            'source': 'excel_job',
                            'match_reason': '基于关键词匹配'
                        })
            
            # 在标准岗位画像中检索
            if use_personas and self.tfidf_persona_documents:
                persona_vecs = self.tfidf_vectorizer.transform(self.tfidf_persona_documents)
                persona_similarities = cosine_similarity(resume_vec, persona_vecs).flatten()
                
                top_persona_indices = np.argsort(persona_similarities)[::-1][:top_k // 2]
                
                for idx in top_persona_indices:
                    if persona_similarities[idx] > 0.1:
                        all_results.append({
                            'job_name': self.tfidf_persona_metadatas[idx]['job_name'],
                            'salary': self.tfidf_persona_metadatas[idx]['salary'],
                            'education': self.tfidf_persona_metadatas[idx]['education'],
                            'experience': self.tfidf_persona_metadatas[idx]['experience'],
                            'skills': self.tfidf_persona_metadatas[idx]['skills'],
                            'similarity': float(persona_similarities[idx]),
                            'source': 'standard_persona',
                            'match_reason': '基于关键词与标准画像匹配'
                        })
        
        # 按相似度排序
        all_results.sort(key=lambda x: x['similarity'], reverse=True)
        
        # 如果返回结果不足 top_k，降低阈值补充结果（最多返回 top_k）
        if len(all_results) < top_k and self.tfidf_job_documents:
            # 重新检索，使用更低阈值
            threshold = 0.001
            extra_results = []
            job_vecs = self.tfidf_vectorizer.transform(self.tfidf_job_documents)
            job_similarities = cosine_similarity(resume_vec, job_vecs).flatten()
            
            # 按相似度排序
            sorted_indices = np.argsort(job_similarities)[::-1]
            
            for idx in sorted_indices:
                if job_similarities[idx] > threshold and len(all_results) + len(extra_results) < top_k:
                    # 检查是否已存在
                    job_name = self.tfidf_job_metadatas[idx]['job_name']
                    company = self.tfidf_job_metadatas[idx]['company']
                    if not any(r['job_name'] == job_name and r['company'] == company for r in all_results + extra_results):
                        extra_results.append({
                            'job_name': job_name,
                            'company': company,
                            'salary': self.tfidf_job_metadatas[idx]['salary'],
                            'education': self.tfidf_job_metadatas[idx].get('education', ''),
                            'experience': self.tfidf_job_metadatas[idx].get('experience', ''),
                            'similarity': float(job_similarities[idx]),
                            'source': 'excel_job',
                            'match_reason': '基于关键词匹配'
                        })
            
            all_results.extend(extra_results)
        
        print(f"   ✅ 匹配完成，返回 {len(all_results[:top_k])} 个岗位")
        return all_results[:top_k]
    
    def get_collection_stats(self):
        """获取统计信息"""
        return {
            'excel_jobs': len(self.tfidf_job_documents),
            'standard_personas': len(self.tfidf_persona_documents),
            'total': len(self.tfidf_job_documents) + len(self.tfidf_persona_documents)
        }


# 余弦相似度计算（避免 sklearn 依赖）
def cosine_similarity(A, B):
    """计算余弦相似度"""
    from sklearn.metrics.pairwise import cosine_similarity as sklearn_cosine
    return sklearn_cosine(A, B)


# 单例模式
_retriever_instance = None

def get_enhanced_retriever(excel_path=None, personas_path=None):
    """获取增强版 RAG 检索器单例"""
    global _retriever_instance
    
    if _retriever_instance is None:
        _retriever_instance = EnhancedRAGRetriever(excel_path, personas_path)
    
    return _retriever_instance
