import axios from 'axios'

const api = axios.create({
  baseURL: '',
  timeout: 30000,
})

export async function submitText(text) {
  const formData = new FormData()
  formData.append('text', text)
  const { data } = await api.post('/verify/text', formData)
  return data
}

export async function submitImage(file) {
  const formData = new FormData()
  formData.append('file', file)
  const { data } = await api.post('/verify/image', formData)
  return data
}

export async function getResult(verificationId) {
  const { data } = await api.get(`/result/${verificationId}`)
  return data
}

export async function fetchResultAudio(verificationId) {
  const { data } = await api.get(`/result/${verificationId}/audio`, {
    responseType: 'blob',
  })
  return data
}
