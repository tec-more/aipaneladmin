import request from '@/utils/request'

// 获取客户列表
export const getCustomerList = (params) => {
  return request.get('/v1/customer/list', { params })
}

// 获取客户详情
export const getCustomerDetail = (id) => {
  return request.get(`/v1/customer/${id}`)
}

// 创建客户
export const createCustomer = (data) => {
  return request.post('/v1/customer', data)
}

// 更新客户
export const updateCustomer = (id, data) => {
  return request.put(`/v1/customer/${id}`, data)
}

// 删除客户
export const deleteCustomer = (id) => {
  return request.delete(`/v1/customer/${id}`)
}

// 批量删除客户
export const batchDeleteCustomer = (ids) => {
  return request.delete('/v1/customer/batch', { data: { ids } })
}

// 启用/禁用客户
export const toggleCustomerStatus = (id) => {
  return request.patch(`/v1/customer/${id}/status`)
}

// 更新客户积分
export const updateCustomerPoints = (id, data) => {
  return request.patch(`/v1/customer/${id}/points`, data)
}

// 更新客户会员到期日期
export const updateCustomerMembership = (id, data) => {
  return request.patch(`/v1/customer/${id}/membership`, data)
}