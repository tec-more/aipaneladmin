import request from '@/utils/request'

const BASE = '/v1/mes'

export const getMaterialList = (params) => {
  return request.get(`${BASE}/base-data/materials`, { params })
}

export const getMaterialDetail = (id) => {
  return request.get(`${BASE}/base-data/materials/${id}`)
}

export const createMaterial = (data) => {
  return request.post(`${BASE}/base-data/materials`, data)
}

export const updateMaterial = (id, data) => {
  return request.put(`${BASE}/base-data/materials/${id}`, data)
}

export const deleteMaterial = (id) => {
  return request.delete(`${BASE}/base-data/materials/${id}`)
}

export const getBomList = (params) => {
  return request.get(`${BASE}/base-data/boms`, { params })
}

export const getBomDetail = (id) => {
  return request.get(`${BASE}/base-data/boms/${id}`)
}

export const getProductBom = (productId, expandLevel) => {
  const params = expandLevel ? { expand_level: expandLevel } : {}
  return request.get(`${BASE}/base-data/products/${productId}/bom`, { params })
}

export const getProductMrp = (productId, quantity) => {
  const params = quantity ? { quantity } : {}
  return request.get(`${BASE}/base-data/products/${productId}/mrp`, { params })
}

export const createBom = (data) => {
  return request.post(`${BASE}/base-data/boms`, data)
}

export const updateBom = (id, data) => {
  return request.put(`${BASE}/base-data/boms/${id}`, data)
}

export const deleteBom = (id) => {
  return request.delete(`${BASE}/base-data/boms/${id}`)
}

export const getBomVersionList = (params) => {
  return request.get(`${BASE}/base-data/bom-versions`, { params })
}

export const getBomVersionDetail = (id) => {
  return request.get(`${BASE}/base-data/bom-versions/${id}`)
}

export const getBomVersionHistory = (product_code) => {
  return request.get(`${BASE}/base-data/bom-versions/${product_code}/history`)
}

export const createBomVersion = (data) => {
  return request.post(`${BASE}/base-data/bom-versions`, data)
}

export const copyBomVersion = (id, data) => {
  return request.post(`${BASE}/base-data/bom-versions/${id}/copy`, data)
}

export const activateBomVersion = (id) => {
  return request.put(`${BASE}/base-data/bom-versions/${id}/activate`)
}

export const obsoleteBomVersion = (id) => {
  return request.put(`${BASE}/base-data/bom-versions/${id}/obsolete`)
}

export const getBomOptions = () => {
  return request.get(`${BASE}/base-data/boms/options`)
}

export const getWorkcenterList = (params) => {
  return request.get(`${BASE}/base-data/work-centers`, { params })
}

export const getWorkcenterDetail = (id) => {
  return request.get(`${BASE}/base-data/work-centers/${id}`)
}

export const createWorkcenter = (data) => {
  return request.post(`${BASE}/base-data/work-centers`, data)
}

export const updateWorkcenter = (id, data) => {
  return request.put(`${BASE}/base-data/work-centers/${id}`, data)
}

export const deleteWorkcenter = (id) => {
  return request.delete(`${BASE}/base-data/work-centers/${id}`)
}

export const getProcessList = (params) => {
  return request.get(`${BASE}/base-data/processes`, { params })
}

export const getProcessDetail = (id) => {
  return request.get(`${BASE}/base-data/processes/${id}`)
}

export const createProcess = (data) => {
  return request.post(`${BASE}/base-data/processes`, data)
}

export const updateProcess = (id, data) => {
  return request.put(`${BASE}/base-data/processes/${id}`, data)
}

export const deleteProcess = (id) => {
  return request.delete(`${BASE}/base-data/processes/${id}`)
}

export const getRouteList = (params) => {
  return request.get(`${BASE}/base-data/routes`, { params })
}

export const getRouteDetail = (id) => {
  return request.get(`${BASE}/base-data/routes/${id}`)
}

export const createRoute = (data) => {
  return request.post(`${BASE}/base-data/routes`, data)
}

export const updateRoute = (id, data) => {
  return request.put(`${BASE}/base-data/routes/${id}`, data)
}

export const deleteRoute = (id) => {
  return request.delete(`${BASE}/base-data/routes/${id}`)
}

export const getProductionPlanList = (params) => {
  return request.get(`${BASE}/production/plans`, { params })
}

export const getProductionPlanDetail = (id) => {
  return request.get(`${BASE}/production/plans/${id}`)
}

export const createProductionPlan = (data) => {
  return request.post(`${BASE}/production/plans`, data)
}

export const updateProductionPlan = (id, data) => {
  return request.put(`${BASE}/production/plans/${id}`, data)
}

export const deleteProductionPlan = (id) => {
  return request.delete(`${BASE}/production/plans/${id}`)
}

export const getProductionOrderList = (params) => {
  return request.get(`${BASE}/production/orders`, { params })
}

export const getProductionOrderDetail = (id) => {
  return request.get(`${BASE}/production/orders/${id}`)
}

export const createProductionOrder = (data) => {
  return request.post(`${BASE}/production/orders`, data)
}

export const updateProductionOrder = (id, data) => {
  return request.put(`${BASE}/production/orders/${id}`, data)
}

export const deleteProductionOrder = (id) => {
  return request.delete(`${BASE}/production/orders/${id}`)
}

export const getQualityInspectionList = (params) => {
  return request.get(`${BASE}/quality/inspections`, { params })
}

export const getQualityInspectionDetail = (id) => {
  return request.get(`${BASE}/quality/inspections/${id}`)
}

export const createQualityInspection = (data) => {
  return request.post(`${BASE}/quality/inspections`, data)
}

export const updateQualityInspection = (id, data) => {
  return request.put(`${BASE}/quality/inspections/${id}`, data)
}

export const deleteQualityInspection = (id) => {
  return request.delete(`${BASE}/quality/inspections/${id}`)
}

export const getEquipmentList = (params) => {
  return request.get(`${BASE}/equipment`, { params })
}

export const getEquipmentDetail = (id) => {
  return request.get(`${BASE}/equipment/${id}`)
}

export const createEquipment = (data) => {
  return request.post(`${BASE}/equipment`, data)
}

export const updateEquipment = (id, data) => {
  return request.put(`${BASE}/equipment/${id}`, data)
}

export const deleteEquipment = (id) => {
  return request.delete(`${BASE}/equipment/${id}`)
}
