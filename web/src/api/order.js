import request from '@/utils/request'

// 获取订单列表
export const getOrderList = (params) => {
  return request.get('/v1/orders/', { params })
}

// 获取订单详情
export const getOrderDetail = (id) => {
  return request.get(`/v1/orders/${id}`)
}

// 创建订单
export const createOrder = (data) => {
  return request.post('/v1/orders/create', data)
}

// 更新订单
export const updateOrder = (id, data) => {
  return request.put(`/v1/orders/${id}`, data)
}

// 删除订单
export const deleteOrder = (id) => {
  return request.delete(`/v1/orders/${id}`)
}

// 批量删除订单
export const batchDeleteOrder = (ids) => {
  return request.delete('/v1/orders/batch', { data: { ids } })
}

// 按客户获取订单
export const getOrdersByCustomer = (customerId, params) => {
  return request.get(`/v1/orders/customer/${customerId}`, { params })
}

// 更新订单状态
export const updateOrderStatus = (id, data) => {
  return request.patch(`/v1/orders/${id}/status`, data)
}

// 更新支付状态
export const updatePaymentStatus = (id, data) => {
  return request.patch(`/v1/orders/${id}/payment-status`, data)
}

// 取消订单
export const cancelOrder = (id) => {
  return request.patch(`/v1/orders/${id}/status`, { status: 'cancelled' })
}

// 完成订单
export const completeOrder = (id) => {
  return request.patch(`/v1/orders/${id}/status`, { status: 'completed' })
}