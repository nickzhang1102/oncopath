import { createRouter, createWebHistory } from 'vue-router'
import { useUserStore } from '@/stores/user'
import { usePatientStore } from '@/stores/patient'
import { showToast } from 'vant'

// 路由配置
const routes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/Login.vue'),
    meta: {
      requiresAuth: false,
      title: '登录'
    }
  },
  {
    path: '/',
    redirect: '/home/main'
  },
  {
    path: '/home',
    name: 'Home',
    component: () => import('@/views/Home.vue'),
    redirect: '/home/main',
    meta: {
      requiresAuth: true,
      title: 'OncoPath'
    },
    children: [
      {
        path: 'main',
        name: 'Main',
        component: () => import('@/views/Main.vue'),
        meta: {
          requiresAuth: true,
          keepAlive: true,
          title: '主页'
        }
      },
      {
        path: 'timeline',
        name: 'Timeline',
        component: () => import('@/views/Timeline.vue'),
        meta: {
          requiresAuth: true,
          keepAlive: true,
          title: '时间线'
        }
      },
      {
        path: 'news',
        name: 'News',
        component: () => import('@/views/NewsView.vue'),
        meta: {
          requiresAuth: true,
          keepAlive: true,
          title: '智能'
        }
      },
      {
        path: 'medical',
        name: 'Medical',
        component: () => import('@/views/MedicalView.vue'),
        meta: {
          requiresAuth: true,
          keepAlive: true,
          title: '病情'
        }
      },
      {
        path: 'profile',
        name: 'Profile',
        component: () => import('@/views/Profile.vue'),
        meta: {
          requiresAuth: true,
          title: '个人中心'
        },
        children: [
          {
            path: 'info',
            name: 'ProfileInfo',
            component: () => import('@/views/profile/ProfileInfo.vue'),
            meta: {
              requiresAuth: true,
              title: '个人信息'
            }
          },
          {
            path: 'password',
            name: 'ProfilePassword',
            component: () => import('@/views/profile/ProfilePassword.vue'),
            meta: {
              requiresAuth: true,
              title: '修改密码'
            }
          },
          {
            path: 'notifications',
            name: 'ProfileNotifications',
            component: () => import('@/views/profile/ProfileNotifications.vue'),
            meta: {
              requiresAuth: true,
              title: '消息通知'
            }
          },
          {
            path: 'privacy',
            name: 'ProfilePrivacy',
            component: () => import('@/views/profile/ProfilePrivacy.vue'),
            meta: {
              requiresAuth: true,
              title: '隐私设置'
            }
          },
          {
            path: 'help',
            name: 'ProfileHelp',
            component: () => import('@/views/profile/ProfileHelp.vue'),
            meta: {
              requiresAuth: true,
              title: '帮助中心'
            }
          },
          {
            path: 'about',
            name: 'ProfileAbout',
            component: () => import('@/views/profile/ProfileAbout.vue'),
            meta: {
              requiresAuth: true,
              title: '关于我们'
            }
          },
          {
            path: 'export',
            name: 'DataExport',
            component: () => import('@/views/profile/DataExportView.vue'),
            meta: {
              requiresAuth: true,
              title: '数据导出'
            }
          }
        ]
      },
      {
        path: 'reports',
        name: 'Reports',
        component: () => import('@/views/Reports.vue'),
        meta: {
          requiresAuth: true,
          keepAlive: true,
          title: '报告列表'
        }
      },
      {
        path: 'report/:id',
        name: 'MedicalRecord',
        component: () => import('@/views/MedicalRecord.vue'),
        meta: {
          requiresAuth: true,
          title: '报告详情'
        }
      },
      // 从顶级路由移入的页面
      {
        path: 'image-report',
        name: 'ImageReport',
        component: () => import('@/views/ImageReportView.vue'),
        meta: {
          requiresAuth: true,
          title: '上传报告'
        }
      },
      {
        path: 'image-report/:id(\\d+)/review',
        name: 'OCRReview',
        component: () => import('@/views/OCRReviewView.vue'),
        meta: {
          requiresAuth: true,
          title: 'OCR审查'
        }
      },
      {
        path: 'exam-reports',
        name: 'ExamReports',
        component: () => import('@/views/ExamReportsView.vue'),
        meta: {
          requiresAuth: true,
          title: '检查报告'
        }
      },
      {
        path: 'pathology-reports',
        name: 'PathologyReports',
        component: () => import('@/views/PathologyReportsView.vue'),
        meta: {
          requiresAuth: true,
          title: '病理报告'
        }
      },
      {
        path: 'exam-report/:id',
        name: 'ExamReportDetail',
        component: () => import('@/views/ExamDetailView.vue'),
        meta: {
          requiresAuth: true,
          title: '检查报告详情'
        }
      },
      {
        path: 'pathology-report/:id',
        name: 'PathologyReportDetail',
        component: () => import('@/views/PathologyDetailView.vue'),
        meta: {
          requiresAuth: true,
          title: '病理报告详情'
        }
      },
      {
        path: 'treatment',
        name: 'Treatment',
        component: () => import('@/views/TreatmentView.vue'),
        meta: {
          requiresAuth: true,
          title: '治疗记录'
        }
      },
      {
        path: 'medication',
        name: 'Medication',
        component: () => import('@/views/MedicationView.vue'),
        meta: {
          requiresAuth: true,
          title: '用药记录'
        }
      },
      {
        path: 'status',
        name: 'Status',
        component: () => import('@/views/StatusView.vue'),
        meta: {
          requiresAuth: true,
          title: '状态记录'
        }
      },
      {
        path: 'index',
        name: 'IndexView',
        component: () => import('@/views/IndexView.vue'),
        meta: {
          requiresAuth: true,
          keepAlive: true,
          title: '指标查询'
        }
      },
      {
        path: 'abnormal-indicators',
        name: 'AbnormalIndicators',
        component: () => import('@/views/AbnormalIndicators.vue'),
        meta: {
          requiresAuth: true,
          title: '异常指标'
        }
      },
      {
        path: 'indicator/history',
        name: 'IndicatorHistory',
        component: () => import('@/views/IndicatorHistory.vue'),
        meta: {
          requiresAuth: true,
          title: '指标历史'
        }
      },
      {
        path: 'consultation',
        name: 'ConsultationList',
        component: () => import('@/views/ConsultationList.vue'),
        meta: {
          requiresAuth: true,
          title: '虚拟会诊'
        }
      },
      {
        path: 'consultation/prompt-config',
        name: 'PromptConfig',
        component: () => import('@/views/PromptConfigView.vue'),
        meta: {
          requiresAuth: true,
          title: '提示词配置'
        }
      },
      {
        path: 'consultation/:token',
        name: 'ConsultationDetail',
        component: () => import('@/views/ConversationDisplay.vue'),
        props: true,
        meta: {
          requiresAuth: true,
          title: '会诊详情'
        }
      },
      {
        path: 'knowledge',
        name: 'Knowledge',
        component: () => import('@/views/KnowledgeView.vue'),
        meta: {
          requiresAuth: true,
          title: '知识库'
        }
      },
      {
        path: 'patient-management',
        name: 'PatientManagement',
        component: () => import('@/views/PatientManagementView.vue'),
        meta: {
          requiresAuth: true,
          title: '病人管理'
        }
      },
      {
        path: 'follow-up',
        name: 'FollowUp',
        component: () => import('@/views/FollowUpView.vue'),
        meta: {
          requiresAuth: true,
          title: '随访提醒'
        }
      },
      {
        path: 'search',
        name: 'Search',
        component: () => import('@/views/SearchView.vue'),
        meta: {
          requiresAuth: true,
          title: '搜索'
        }
      }
    ]
  },
  {
    path: '/admin',
    name: 'AdminLayout',
    component: () => import('@/views/admin/AdminLayout.vue'),
    redirect: '/admin/dashboard',
    meta: {
      requiresAuth: true,
      requiresAdmin: true,
      title: '管理后台'
    },
    children: [
      {
        path: 'dashboard',
        name: 'AdminDashboard',
        component: () => import('@/views/admin/AdminHome.vue'),
        meta: {
          requiresAuth: true,
          requiresAdmin: true,
          title: '仪表盘'
        }
      },
      {
        path: 'users',
        name: 'AdminUsers',
        component: () => import('@/views/admin/AdminUsers.vue'),
        meta: {
          requiresAuth: true,
          requiresAdmin: true,
          title: '用户管理'
        }
      },
      {
        path: 'indices',
        name: 'AdminIndices',
        component: () => import('@/views/admin/AdminIndices.vue'),
        meta: {
          requiresAuth: true,
          requiresAdmin: true,
          title: '指标库管理'
        }
      },
      {
        path: 'categories',
        name: 'AdminCategories',
        component: () => import('@/views/admin/AdminCategories.vue'),
        meta: {
          requiresAuth: true,
          requiresAdmin: true,
          title: '分类管理'
        }
      },
      {
        path: 'llm-configs',
        name: 'AdminLLMConfigs',
        component: () => import('@/views/admin/AdminLLMConfigs.vue'),
        meta: {
          requiresAuth: true,
          requiresAdmin: true,
          title: 'LLM配置'
        }
      },
      {
        path: 'agentteams-config',
        name: 'AdminAgentTeamsConfig',
        component: () => import('@/views/admin/AdminAgentTeamsConfig.vue'),
        meta: {
          requiresAuth: true,
          requiresAdmin: true,
          title: 'AgentTeams配置'
        }
      }
    ]
  },
  {
    path: '/share/report/:token',
    name: 'ShareReport',
    component: () => import('@/views/ShareReport.vue'),
    meta: {
      requiresAuth: false,
      title: '报告分享'
    }
  },
  {
    path: '/share/:token',
    name: 'ShareConsultation',
    component: () => import('@/views/ShareConsultation.vue'),
    meta: {
      requiresAuth: false,
      title: '会诊分享'
    }
  },
  {
    path: '/:pathMatch(.*)*',
    name: 'NotFound',
    component: () => import('@/views/NotFound.vue'),
    meta: {
      requiresAuth: false,
      title: '页面未找到'
    }
  }
]

// 创建路由实例
const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior(to, from, savedPosition) {
    if (savedPosition) {
      return savedPosition
    } else {
      return { top: 0 }
    }
  }
})

// 路由守卫
router.beforeEach(async (to, from, next) => {
  // 设置页面标题
  document.title = to.meta.title ? `${to.meta.title} - OncoPath` : 'OncoPath'

  const userStore = useUserStore()

  // 检查是否需要登录
  if (to.meta.requiresAuth !== false) {
    if (!userStore.isLoggedIn) {
      // 未登录，跳转到登录页
      next({
        path: '/login',
        query: { redirect: to.fullPath }
      })
      return
    }

    // 管理员页面需要同步等待 userInfo（因为需要检查 account_type）
    if (to.meta.requiresAdmin) {
      if (!userStore.userInfo) {
        if (!router._userInfoPromise) {
          router._userInfoPromise = userStore.fetchUserInfo().finally(() => {
            router._userInfoPromise = null
          })
        }
        try {
          await router._userInfoPromise
        } catch (error) {
          console.error('获取用户信息失败:', error)
          next({ path: '/home' })
          return
        }
      }
      // 检查管理员权限
      if (userStore.userInfo?.account_type !== 'admin') {
        next({ path: '/home' })
        return
      }
    }

    // 普通路由：先放行，后台异步加载用户信息和患者数据
    next()

    // 放行后异步加载（不阻塞导航）
    if (!userStore.userInfo) {
      userStore.fetchUserInfo().catch(err => {
        console.error('获取用户信息失败:', err)
      })
    }

    const patientStore = usePatientStore()
    if (!patientStore.loaded) {
      patientStore.fetchPatientList().catch(err => {
        console.error('加载患者列表失败:', err)
      })
    }
    return
  }

  // 已登录用户访问登录页，重定向到首页
  if (to.path === '/login' && userStore.isLoggedIn) {
    // 重置 401 跳转标志，用户已重新登录
    import('@/api/request.js').then(m => { m.resetRedirectFlag() }).catch(() => {})
    next({ path: '/' })
    return
  }

  next()
})

export default router
