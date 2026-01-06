import request from '@/utils/request'

// 获取订单列表
export const getOrderList = (params) => {
  return request.get('/api/v1/order/list', { params })
}

// 获取订单详情
export const getOrderDetail = (id) => {
  return request.get(`/api/v1/order/${id}`)
}

// 创建订单
export const createOrder = (data) => {
  return request.post('/api/v1/order', data)
}

// 更新订单
export const updateOrder = (id, data) => {
  return request.put(`/api/v1/order/${id}`, data)
}

// 删除订单
export const deleteOrder = (id) => {
  return request.delete(`/api/v1/order/${id}`)
}

// 批量删除订单
export const batchDeleteOrder = (ids) => {
  return request.delete('/api/v1/order/batch', { data: { ids } })
}

// 按客户获取订单
export const getOrdersByCustomer = (customerId, params) => {
  return request.get(`/api/v1/order/customer/${customerId}`, { params })
}

// 更新订单状态
export const updateOrderStatus = (id, data) => {
  return request.patch(`/api/v1/order/${id}/status`, data)
}

// 更新支付状态
export const updatePaymentStatus = (id, data) => {
  return request.patch(`/api/v1/order/${id}/payment-status`, data)
}