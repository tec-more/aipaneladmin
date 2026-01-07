import request from '@/utils/request'

// 获取产品列表
export const getProductList = (params) => {
  return request.get('/v1/product/list', { params })
}

// 获取产品详情
export const getProductDetail = (id) => {
  return request.get(`/v1/product/${id}`)
}

// 创建产品
export const createProduct = (data) => {
  return request.post('/v1/product', data)
}

// 更新产品
export const updateProduct = (id, data) => {
  return request.put(`/v1/product/${id}`, data)
}

// 删除产品
export const deleteProduct = (id) => {
  return request.delete(`/v1/product/${id}`)
}

// 批量删除产品
export const batchDeleteProduct = (ids) => {
  return request.delete('/v1/product/batch', { data: { ids } })
}

// 更新产品库存
export const updateProductStock = (id, data) => {
  return request.patch(`/v1/product/${id}/stock`, data)
}

// 上下架产品
export const toggleProductStatus = (id) => {
  return request.patch(`/v1/product/${id}/toggle-status`)
}