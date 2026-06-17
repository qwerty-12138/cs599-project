import { defineStore } from 'pinia'
import { ref } from 'vue'
import { knowledgeApi } from '@/api'
import type { Document, DocumentDetail, DocumentChunk } from '@/types'

export const useKnowledgeStore = defineStore('knowledge', () => {
  const documents = ref<Document[]>([])
  const total = ref(0)
  const currentPage = ref(1)
  const pageSize = ref(10)
  const loading = ref(false)
  const searchKeyword = ref('')
  const searchType = ref('')

  const currentDocument = ref<DocumentDetail | null>(null)
  const documentChunks = ref<DocumentChunk[]>([])
  const loadingChunks = ref(false)

  async function loadDocuments() {
    loading.value = true
    try {
      const res = await knowledgeApi.getDocuments(
        currentPage.value, pageSize.value,
        searchKeyword.value, searchType.value
      )
      documents.value = res.list
      total.value = res.total
    } finally {
      loading.value = false
    }
  }

  async function loadDocumentDetail(id: string) {
    currentDocument.value = await knowledgeApi.getDocument(id)
    loadingChunks.value = true
    try {
      documentChunks.value = await knowledgeApi.getDocumentChunks(id)
    } finally {
      loadingChunks.value = false
    }
  }

  async function uploadDocument(file: File, name?: string) {
    await knowledgeApi.uploadDocument(file, name)
    await loadDocuments()
  }

  async function deleteDocument(id: string) {
    await knowledgeApi.deleteDocument(id)
    await loadDocuments()
  }

  function setPage(page: number) { currentPage.value = page }
  function setPageSize(size: number) { pageSize.value = size; currentPage.value = 1 }
  function setSearch(keyword: string, type: string) {
    searchKeyword.value = keyword
    searchType.value = type
    currentPage.value = 1
  }

  return {
    documents, total, currentPage, pageSize, loading,
    searchKeyword, searchType,
    currentDocument, documentChunks, loadingChunks,
    loadDocuments, loadDocumentDetail, uploadDocument, deleteDocument,
    setPage, setPageSize, setSearch
  }
})
