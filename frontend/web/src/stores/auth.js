import { defineStore } from 'pinia'
import { ref } from 'vue'
import { authApi } from '../api'

export const useAuthStore = defineStore('auth', () => {
  const token = ref(localStorage.getItem('token') || '')
  const role = ref(localStorage.getItem('role') || '')
  const username = ref(localStorage.getItem('username') || '')

  function _set(t, r, u) {
    token.value = t; role.value = r; username.value = u
    localStorage.setItem('token', t)
    localStorage.setItem('role', r)
    localStorage.setItem('username', u)
  }

  async function login(u, p) {
    const { data } = await authApi.login(u, p)
    _set(data.access_token, data.role, u)
    return data
  }

  async function register(payload) {
    const { data } = await authApi.register(payload)
    _set(data.access_token, data.role, payload.username)
    return data
  }

  function logout() {
    token.value = ''; role.value = ''; username.value = ''
    localStorage.removeItem('token')
    localStorage.removeItem('role')
    localStorage.removeItem('username')
  }

  const isAuthed = () => !!token.value

  return { token, role, username, login, register, logout, isAuthed }
})
