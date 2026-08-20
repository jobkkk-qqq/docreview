<template>
  <div class="document-manage">
    <!-- 搜索栏 -->
    <el-card shadow="never" class="search-card">
      <el-form :inline="true" :model="searchForm" class="search-form">
        <el-form-item label="关键词">
          <el-input
            v-model="searchForm.keyword"
            placeholder="搜索文档标题/编号"
            clearable
            style="width: 200px"
            @keyup.enter="handleSearch"
          />
        </el-form-item>
        <el-form-item label="一级分类">
          <el-select v-model="searchForm.category_id" placeholder="全部分类" clearable style="width: 160px">
            <el-option v-for="item in categoryOptions" :key="item.id" :label="item.name" :value="item.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="部门">
          <el-select v-model="searchForm.department_id" placeholder="全部部门" clearable style="width: 140px">
            <el-option v-for="item in departmentOptions" :key="item.id" :label="item.name" :value="item.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="文档级别">
          <el-select v-model="searchForm.doc_level" placeholder="全部级别" clearable style="width: 130px">
            <el-option v-for="lv in docLevels" :key="lv" :label="lv" :value="lv" />
          </el-select>
        </el-form-item>
        <el-form-item label="保密等级">
          <el-select v-model="searchForm.confidential_level" placeholder="全部等级" clearable style="width: 140px">
            <el-option label="公开" value="public" />
            <el-option label="内部" value="internal" />
            <el-option label="机密" value="confidential" />
            <el-option label="绝密" value="top_secret" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :icon="Search" @click="handleSearch">搜索</el-button>
          <el-button :icon="Refresh" @click="handleReset">重置</el-button>
        </el-form-item>
      </el-form>

      <!-- 视图切换 -->
      <div class="view-toggle">
        <el-tooltip content="卡片视图" placement="top">
          <el-button
            :type="viewMode === 'card' ? 'primary' : 'default'"
            :icon="Grid"
            circle
            size="small"
            @click="setViewMode('card')"
          />
        </el-tooltip>
        <el-tooltip content="列表视图" placement="top">
          <el-button
            :type="viewMode === 'list' ? 'primary' : 'default'"
            :icon="List"
            circle
            size="small"
            @click="setViewMode('list')"
          />
        </el-tooltip>
      </div>
    </el-card>

    <!-- 分组文档列表 -->
    <div class="doc-groups" v-loading="loading">
      <template v-if="categoryGroups.length > 0">
        <div
          v-for="group in categoryGroups"
          :key="group.id ?? '__uncat__'"
          class="doc-group"
        >
          <!-- 分类标题栏 -->
          <div class="group-header" @click="toggleGroup(group)">
            <div class="group-header-left">
              <el-icon class="group-toggle-icon" :class="{ rotated: group._expanded !== false }">
                <ArrowDown />
              </el-icon>
              <el-icon class="group-folder-icon"><FolderOpened /></el-icon>
              <span class="group-name">{{ group.name }}</span>
              <el-tag size="small" type="info" effect="plain" class="group-count">
                第 {{ group._page || 1 }}/{{ Math.ceil(group.total / 30) || 1 }} 页，{{ group.documents.length }} / {{ group.total }} 个
              </el-tag>
            </div>
            <div class="group-header-right">
              <span class="group-latest">最近上传</span>
            </div>
          </div>

          <!-- 文档卡片网格 -->
          <el-collapse-transition>
            <div v-show="group._expanded !== false" v-if="viewMode === 'card'" class="doc-cards">
              <div
                v-for="doc in group.documents"
                :key="doc.id"
                class="doc-card"
                @click="handleView(doc)"
              >
                <!-- 卡片顶部：文件类型图标区 -->
                <div class="card-top">
                  <div class="card-type-icon" :class="'type-' + (doc.file_name ? (doc.file_name.split('.').pop()||'').toLowerCase() : 'unknown')">
                    <span class="type-text">{{ (doc.file_name||'?').split('.').pop()?.toUpperCase() || '?' }}</span>
                  </div>
                  <!-- 保密等级角标 -->
                  <el-tag
                    class="card-conf-level"
                    :type="confidentialityTagType(doc.confidential_level)"
                    size="small"
                    effect="light"
                  >
                    {{ confidentialityLabel(doc.confidential_level) }}
                  </el-tag>
                </div>

                <!-- 文档标题 -->
                <div class="card-title" :title="doc.title">{{ doc.title }}</div>

                <!-- 文档编号 -->
                <div class="card-doc-no" v-if="doc.doc_no">
                  <el-icon><Document /></el-icon>
                  {{ doc.doc_no }}
                </div>

                <!-- 部门 / 文档级别 -->
                <div class="card-dep-level">
                  <el-tag v-if="doc.department" size="small" type="info" effect="plain">{{ doc.department.name }}</el-tag>
                  <el-tag v-if="doc.doc_level && doc.doc_level !== '无级别'" size="small" type="primary" effect="plain">{{ doc.doc_level }}</el-tag>
                </div>

                <!-- 底部信息栏 -->
                <div class="card-footer">
                  <div class="card-meta">
                    <el-icon><Clock /></el-icon>
                    <span>{{ formatDate(doc.created_at) }}</span>
                  </div>
                  <div class="card-uploader" v-if="doc.uploader">
                    <el-icon><User /></el-icon>
                    <span>{{ doc.uploader.display_name || doc.uploader.username }}</span>
                  </div>
                </div>

                <!-- 悬浮操作栏 -->
                <div class="card-actions" @click.stop>
                  <el-button type="primary" link size="small" @click.stop="handleView(doc)">查看</el-button>
                  <el-button v-if="canEdit" type="warning" link size="small" @click.stop="handleEdit(doc)">编辑</el-button>
                  <el-button type="success" link size="small" @click.stop="handleDownload(doc)">下载</el-button>
                  <el-button
                    v-if="isPreviewable(doc.file_name) && doc.can_download"
                    type="primary"
                    link
                    size="small"
                    @click.stop="handlePreview(doc)"
                  >预览</el-button>
                  <el-button
                    v-if="canManagePermissions"
                    type="info"
                    link
                    size="small"
                    @click.stop="handlePermission(doc)"
                  >权限</el-button>
                  <el-button v-if="canDelete" type="danger" link size="small" @click.stop="handleDelete(doc)">删除</el-button>
                </div>
              </div>
            </div>
          </el-collapse-transition>

          <!-- 文档列表视图 -->
          <el-collapse-transition>
            <div v-show="group._expanded !== false" v-if="viewMode === 'list'" class="doc-list">
              <el-table :data="group.documents" stripe size="small" style="width: 100%">
                <el-table-column label="文件名" min-width="240">
                  <template #default="{ row }">
                    <div class="list-file-name" @click="handleView(row)">
                      <el-tag
                        size="small"
                        :type="fileTypeTagType(row.file_name)"
                        effect="light"
                        class="list-type-tag"
                      >
                        {{ (row.file_name||'?').split('.').pop()?.toUpperCase() || '?' }}
                      </el-tag>
                      <span class="list-title" :title="row.title">{{ row.title }}</span>
                    </div>
                  </template>
                </el-table-column>
                <el-table-column label="文档编号" prop="doc_no" width="146" align="right" show-overflow-tooltip />
                <el-table-column label="保密等级" width="116" align="right">
                  <template #default="{ row }">
                    <el-tag :type="confidentialityTagType(row.confidential_level)" size="small">
                      {{ confidentialityLabel(row.confidential_level) }}
                    </el-tag>
                  </template>
                </el-table-column>
                <el-table-column label="部门" width="108" align="right">
                  <template #default="{ row }">
                    {{ row.department?.name || '-' }}
                  </template>
                </el-table-column>
                <el-table-column label="文档级别" width="92" align="left">
                  <template #default="{ row }">
                    <el-tag v-if="row.doc_level && row.doc_level !== '无级别'" size="small" type="primary" effect="plain">
                      {{ row.doc_level }}
                    </el-tag>
                    <span v-else>-</span>
                  </template>
                </el-table-column>
                <el-table-column label="上传人" width="96" header-align="center">
                  <template #default="{ row }">
                    {{ row.uploader?.display_name || row.uploader?.username || '-' }}
                  </template>
                </el-table-column>
                <el-table-column label="上传时间" width="126" header-align="center">
                  <template #default="{ row }">
                    {{ formatDate(row.created_at) }}
                  </template>
                </el-table-column>
                <el-table-column label="操作" width="340" fixed="right">
                  <template #default="{ row }">
                    <div class="table-op-btns">
                    <el-button type="primary" link size="small" @click.stop="handleView(row)">查看</el-button>
                    <el-button v-if="canEdit" type="warning" link size="small" @click.stop="handleEdit(row)">编辑</el-button>
                    <el-button type="success" link size="small" @click.stop="handleDownload(row)">下载</el-button>
                    <el-button
                      v-if="isPreviewable(row.file_name) && row.can_download"
                      type="primary"
                      link
                      size="small"
                      @click.stop="handlePreview(row)"
                    >预览</el-button>
                    <el-button
                      v-if="canManagePermissions"
                      type="info"
                      link
                      size="small"
                      @click.stop="handlePermission(row)"
                    >权限</el-button>
                    <el-button v-if="canDelete" type="danger" link size="small" @click.stop="handleDelete(row)">删除</el-button>
                    </div>
                  </template>
                </el-table-column>
              </el-table>
            </div>
          </el-collapse-transition>

          <!-- 组内分页 -->
          <div v-if="group.total > 30" class="group-pagination">
            <el-pagination
              small
              layout="prev, pager, next"
              :current-page="group._page"
              :page-size="30"
              :total="group.total"
              @current-change="(p) => handleGroupPageChange(group.id, p)"
            />
          </div>
        </div>
      </template>

      <!-- 空状态 -->
      <el-empty v-else-if="!loading" description="暂无符合条件的文档">
        <template #image>
          <el-icon :size="60" color="#c0c4cc"><FolderDelete /></el-icon>
        </template>
        <el-button v-if="canUpload" type="primary" :icon="Upload" @click="$router.push('/documents/upload')">
          上传文档
        </el-button>
      </el-empty>
    </div>

    <!-- 文档详情对话框 -->
    <el-dialog v-model="detailVisible" title="文档详情" width="650px" destroy-on-close>
      <el-descriptions :column="2" border v-if="currentDoc">
        <el-descriptions-item label="文档编号" :span="2">{{ currentDoc.doc_no }}</el-descriptions-item>
        <el-descriptions-item label="文档标题" :span="2">{{ currentDoc.title }}</el-descriptions-item>
        <el-descriptions-item label="分类">{{ currentDoc.category?.name || '-' }}</el-descriptions-item>
        <el-descriptions-item label="部门">{{ currentDoc.department?.name || '-' }}</el-descriptions-item>
        <el-descriptions-item label="文档级别">
          <el-tag v-if="currentDoc.doc_level && currentDoc.doc_level !== '无级别'" size="small" type="primary" effect="plain">
            {{ currentDoc.doc_level }}
          </el-tag>
          <span v-else>-</span>
        </el-descriptions-item>
        <el-descriptions-item label="保密等级">
          <el-tag :type="confidentialityTagType(currentDoc.confidential_level)" size="small">
            {{ confidentialityLabel(currentDoc.confidential_level) }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="上传人">{{ currentDoc.uploader?.display_name || '-' }}</el-descriptions-item>
        <el-descriptions-item label="上传时间">{{ currentDoc.created_at }}</el-descriptions-item>
        <el-descriptions-item label="文件大小">{{ formatFileSize(currentDoc.file_size) }}</el-descriptions-item>
        <el-descriptions-item label="文件格式">{{ currentDoc.file_type || '-' }}</el-descriptions-item>
        <el-descriptions-item label="文档描述" :span="2">{{ currentDoc.summary || '无' }}</el-descriptions-item>
      </el-descriptions>
      <template #footer>
        <el-button @click="detailVisible = false">关闭</el-button>
        <el-button type="success" @click="handleDownload(currentDoc)">下载文档</el-button>
      </template>
    </el-dialog>

    <!-- 编辑文档对话框 -->
    <el-dialog v-model="editVisible" title="编辑文档" width="600px" destroy-on-close draggable>
      <el-form ref="editFormRef" :model="editForm" :rules="editRules" label-width="100px" v-if="editDoc">
        <el-form-item label="文档编号">
          <el-input v-model="editForm.doc_no" placeholder="不填则保留原编号" />
        </el-form-item>
        <el-form-item label="文档标题" prop="title">
          <el-input v-model="editForm.title" placeholder="请输入文档标题" />
        </el-form-item>
        <el-form-item label="文档描述" prop="summary">
          <el-input v-model="editForm.summary" type="textarea" :rows="3" placeholder="文档描述（选填）" />
        </el-form-item>
        <el-form-item label="分类" prop="category_id">
          <el-select v-model="editForm.category_id" placeholder="请选择分类" style="width: 100%">
            <el-option v-for="item in categoryOptions" :key="item.id" :label="item.name" :value="item.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="部门">
          <el-select v-model="editForm.department_id" placeholder="请选择部门" clearable style="width: 100%">
            <el-option v-for="item in departmentOptions" :key="item.id" :label="item.name" :value="item.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="文档级别">
          <el-select v-model="editForm.doc_level" placeholder="请选择文档级别" style="width: 100%">
            <el-option v-for="lv in docLevels" :key="lv" :label="lv" :value="lv" />
          </el-select>
        </el-form-item>
        <el-form-item label="保密等级" prop="confidential_level">
          <el-radio-group v-model="editForm.confidential_level">
            <el-radio value="public">公开</el-radio>
            <el-radio value="internal">内部</el-radio>
            <el-radio value="confidential">机密</el-radio>
            <el-radio value="top_secret">绝密</el-radio>
          </el-radio-group>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="editVisible = false">取消</el-button>
        <el-button type="primary" :loading="editSubmitting" @click="handleEditSubmit">保存</el-button>
      </template>
    </el-dialog>

    <!-- 文档预览对话框 -->
    <el-dialog v-model="previewVisible" title="文档预览" width="90%" fullscreen destroy-on-close draggable>
      <div v-if="previewLoading" class="preview-loading">
        <el-skeleton :rows="10" animated />
      </div>
      <div v-else-if="previewError" class="preview-error">
        <el-result icon="error" title="预览加载失败" sub-title="请稍后重试或下载后查看">
          <template #extra>
            <el-button type="primary" @click="handleDownloadFromPreview">下载查看</el-button>
          </template>
        </el-result>
      </div>
      <div v-else-if="previewUnsupported" class="preview-unsupported">
        <el-result icon="warning" :title="previewErrorTitle" :sub-title="previewErrorMessage">
          <template #extra>
            <el-button type="primary" @click="handleDownloadFromPreview">下载查看</el-button>
          </template>
        </el-result>
      </div>
      <embed v-else-if="previewUrl && previewType === 'pdf'" :src="previewUrl" class="preview-iframe" type="application/pdf" />
      <div v-else-if="previewUrl && previewType === 'txt'" class="preview-txt">
        <pre>{{ previewText }}</pre>
      </div>
      <div v-else-if="previewUrl && previewType === 'image'" class="preview-image">
        <img :src="previewUrl" class="preview-img" />
      </div>
    </el-dialog>

    <!-- 权限管理对话框 -->
    <el-dialog v-model="permVisible" title="文档权限管理" width="700px" destroy-on-close draggable>
      <div v-if="permDoc">
        <div class="perm-header">
          <el-icon :size="16" color="#165dff"><Document /></el-icon>
          <strong>{{ permDoc.title }}</strong>
          <span style="color:#86909c;font-size:12px">（{{ permDoc.doc_no }}）</span>
        </div>

        <!-- 已有权限列表 -->
        <div class="perm-section-title">
          <el-icon><Lock /></el-icon> 已授权列表
        </div>
        <el-table :data="permList" border size="small" style="margin-bottom:16px" max-height="240">
          <el-table-column label="被授权对象" min-width="160">
            <template #default="{ row }">
              <template v-if="row.user_name">
                <el-icon><User /></el-icon> {{ row.user_name }}
              </template>
              <template v-else-if="row.role_name">
                <el-tag size="small" type="success" effect="dark">
                  <el-icon style="margin-right:2px"><Avatar /></el-icon>
                  {{ row.role_name }}
                </el-tag>
              </template>
              <template v-else>-</template>
            </template>
          </el-table-column>
          <el-table-column label="查看" width="70" align="center">
            <template #default="{ row }">
              <el-switch :model-value="row.can_view" disabled size="small" />
            </template>
          </el-table-column>
          <el-table-column label="下载" width="70" align="center">
            <template #default="{ row }">
              <el-switch :model-value="row.can_download" disabled size="small" />
            </template>
          </el-table-column>
          <el-table-column label="编辑" width="70" align="center">
            <template #default="{ row }">
              <el-switch :model-value="row.can_edit" disabled size="small" />
            </template>
          </el-table-column>
          <el-table-column label="操作" width="80">
            <template #default="{ row }">
              <el-button type="danger" link size="small" @click="handleRevokePerm(row.id)">撤销</el-button>
            </template>
          </el-table-column>
        </el-table>

        <!-- 新增权限 -->
        <div class="perm-section-title">
          <el-icon><Plus /></el-icon> 新增授权
        </div>
        <el-form :inline="true" class="perm-form">
          <el-form-item label="用户">
            <el-select
              v-model="newPerm.user_id"
              placeholder="搜索用户"
              filterable
              remote
              :remote-method="searchUsers"
              :loading="userSearchLoading"
              style="width:180px"
              clearable
            >
              <el-option
                v-for="u in userOptions"
                :key="u.id"
                :label="`${u.display_name || u.username}（${u.username}）`"
                :value="u.id"
              />
            </el-select>
          </el-form-item>
          <el-form-item label="或角色">
            <el-select v-model="newPerm.role_id" placeholder="选择角色" clearable style="width:160px">
              <el-option v-for="r in roleOptions" :key="r.id" :label="r.name" :value="r.id" />
            </el-select>
          </el-form-item>
          <el-form-item>
            <el-checkbox v-model="newPerm.can_view">查看</el-checkbox>
            <el-checkbox v-model="newPerm.can_download">下载</el-checkbox>
            <el-checkbox v-model="newPerm.can_edit">编辑</el-checkbox>
          </el-form-item>
          <el-form-item>
            <el-button type="primary" :loading="permSaving" @click="handleGrantPerm" :icon="Plus">授权</el-button>
          </el-form-item>
        </el-form>
      </div>
    </el-dialog>

    <!-- 批量授权对话框 -->
    <el-dialog v-model="batchPermVisible" title="批量授权" width="700px" destroy-on-close draggable>
      <div class="batch-perm-content">
        <div class="batch-perm-info">
          <el-icon :size="16" color="#e6a23c"><WarningFilled /></el-icon>
          已选 <strong>{{ selectedDocs.length }}</strong> 个文档进行批量授权
        </div>

        <!-- 用户选择 -->
        <div class="perm-section-title">
          <el-icon><User /></el-icon> 授权用户
        </div>
        <div class="batch-user-section">
          <el-form :inline="true">
            <el-form-item label="按部门添加">
              <el-select v-model="batchPerm.dept_id" placeholder="选择部门" clearable style="width:180px" @change="handleDeptChange">
                <el-option v-for="d in deptOptions" :key="d.id" :label="d.name" :value="d.id" />
              </el-select>
            </el-form-item>
            <el-form-item label="单独添加">
              <el-select
                v-model="batchPerm.addUser"
                placeholder="搜索用户名"
                filterable
                remote
                :remote-method="searchUsers"
                :loading="userSearchLoading"
                style="width:200px"
                @change="handleAddUser"
              >
                <el-option
                  v-for="u in userOptions"
                  :key="u.id"
                  :label="`${u.display_name || u.username}（${u.username}）`"
                  :value="u.id"
                />
              </el-select>
            </el-form-item>
          </el-form>
          <div class="batch-tags">
            <span class="batch-tags-label">已选用户：</span>
            <template v-if="batchPerm.user_ids.length > 0">
              <el-tag v-for="uid in batchPerm.user_ids" :key="uid" closable size="small" type="info" style="margin:2px 4px" @close="handleRemoveUser(uid)">
                {{ batchUserLabel(uid) }}
              </el-tag>
            </template>
            <span v-else style="color:#c9cdd4;font-size:13px">暂无，请从部门或搜索添加</span>
          </div>
        </div>

        <!-- 角色选择 -->
        <div class="perm-section-title">
          <el-icon><Avatar /></el-icon> 授权角色
        </div>
        <div class="batch-role-section">
          <el-form :inline="true">
            <el-form-item label="添加角色">
              <el-select v-model="batchPerm.addRole" placeholder="选择角色授予权限" clearable style="width:200px" @change="handleAddRole">
                <el-option v-for="r in roleOptions" :key="r.id" :label="r.name" :value="r.id" />
              </el-select>
            </el-form-item>
          </el-form>
          <div class="batch-tags">
            <span class="batch-tags-label">已选角色：</span>
            <template v-if="batchPerm.role_ids.length > 0">
              <el-tag v-for="rid in batchPerm.role_ids" :key="rid" closable size="small" style="margin:2px 4px" @close="handleRemoveRole(rid)">
                <el-icon style="margin-right:2px"><Avatar /></el-icon>
                {{ batchRoleLabel(rid) }}
              </el-tag>
            </template>
            <span v-else style="color:#c9cdd4;font-size:13px">可选，选择角色后该角色下所有用户自动获得权限</span>
          </div>
        </div>

        <!-- 权限选择 -->
        <div class="perm-section-title">
          <el-icon><Setting /></el-icon> 授予权限
        </div>
        <el-checkbox v-model="batchPerm.can_view">查看</el-checkbox>
        <el-checkbox v-model="batchPerm.can_download" style="margin-left:16px">下载</el-checkbox>
        <el-checkbox v-model="batchPerm.can_edit" style="margin-left:16px">编辑</el-checkbox>
      </div>

      <template #footer>
        <el-button @click="batchPermVisible = false">取消</el-button>
        <el-button type="primary" :loading="batchPermSaving" @click="handleBatchPermSubmit">
          确认批量授权
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  Search, Refresh, Upload, Document, Setting, WarningFilled, ArrowDown,
  FolderOpened, FolderDelete, Clock, Grid, List, User
} from '@element-plus/icons-vue'
import {
  getDocumentGrouped, getDocumentDetail, downloadDocument, deleteDocument,
  updateDocument, reportPreviewLog, getDocPermissions, grantDocPermission,
  revokeDocPermission, getDocLevels
} from '../api/document.js'
import { getCategoryListSimple } from '../api/category.js'
import { getDepartmentSimple } from '../api/department.js'
import { getUserList } from '../api/user.js'
import { getRoleList } from '../api/role.js'
import { canUploadDoc, canModifyDoc, canDeleteDoc, canManageDocPermissions } from '../utils/permission.js'
import { isPreviewable, getPreviewType, OFFICE_EXTS, IMAGE_MIME_MAP } from '../utils/preview.js'
import { saveBlobAsFile } from '../utils/download.js'
import { formatDate, formatFileSize, fileTypeTagType, confidentialityTagType, confidentialityLabel } from '../utils/format.js'
import { useMobile } from '../composables/useMobile.js'
import request from '../api/request.js'

const loading = ref(false)
const categoryGroups = ref([])

// 视图模式：card / list，持久化到 localStorage
const VIEW_MODE_KEY = 'docmanage_view_mode'
const viewMode = ref(localStorage.getItem(VIEW_MODE_KEY) || 'card')
function setViewMode(mode) {
  viewMode.value = mode
  localStorage.setItem(VIEW_MODE_KEY, mode)
}

// 移动端检测（使用公共 composable）
const { isMobile } = useMobile()

// 搜索
const categoryOptions = ref([])
const departmentOptions = ref([])
const docLevels = ref(['无级别'])
const searchForm = reactive({ keyword: '', category_id: '', department_id: '', doc_level: '', confidential_level: '' })

// 详情
const detailVisible = ref(false)
const currentDoc = ref(null)

// 编辑
const editVisible = ref(false)
const editSubmitting = ref(false)
const editFormRef = ref(null)
const editDoc = ref(null)
const editForm = reactive({ title: '', doc_no: '', summary: '', category_id: '', department_id: '', doc_level: '无级别', confidential_level: '' })
const editRules = { title: [{ required: true, message: '请输入文档标题', trigger: 'blur' }] }

// 预览
const previewVisible = ref(false)
const previewLoading = ref(false)
const previewUrl = ref('')
const previewType = ref('')
const previewText = ref('')
const previewError = ref(false)
const previewUnsupported = ref(false)
const previewDownloadRow = ref(null)
const previewErrorTitle = ref('无法预览')
const previewErrorMessage = ref('该文件格式暂不支持在线预览，请下载后查看')

// 权限管理
const permVisible = ref(false)
const permDoc = ref(null)
const permList = ref([])
const permSaving = ref(false)
const userSearchLoading = ref(false)
const userOptions = ref([])
const roleOptions = ref([])
const newPerm = reactive({ user_id: null, role_id: null, can_view: true, can_download: true, can_edit: false })

// 批量选择
const selectedDocs = ref([])

// 批量授权
const batchPermVisible = ref(false)
const batchPermSaving = ref(false)
const deptOptions = ref([])
const batchUserMap = ref({})
const batchRoleMap = ref({})
const batchPerm = reactive({
  dept_id: null, addUser: null, addRole: null,
  user_ids: [], role_ids: [],
  can_view: true, can_download: true, can_edit: false,
})

// 权限计算
const canUpload = computed(() => canUploadDoc())
const canDelete = computed(() => canDeleteDoc())
const canEdit = computed(() => canModifyDoc())
const canManagePermissions = computed(() => canManageDocPermissions())

// ── 分组折叠 ──

function toggleGroup(group) {
  if (group._expanded === undefined) {
    group._expanded = false
  } else {
    group._expanded = !group._expanded
  }
}

// ── 数据加载 ──

async function fetchGroupedDocuments() {
  loading.value = true
  try {
    const params = {
      keyword: searchForm.keyword || undefined,
      category_id: searchForm.category_id || undefined,
      department_id: searchForm.department_id || undefined,
      doc_level: searchForm.doc_level || undefined,
      confidential_level: searchForm.confidential_level || undefined,
      page: 1,
      page_size: 30,
    }
    const res = await getDocumentGrouped(params)
    const groups = res || []
    categoryGroups.value = groups.map(g => ({
      ...g,
      _page: 1,
      _expanded: true,
    }))
  } catch { /* ignore */ } finally { loading.value = false }
}
async function fetchCategories() {
  try {
    const res = await getCategoryListSimple()
    categoryOptions.value = res.items || res.data || res || []
  } catch { /* ignore */ }
}
async function fetchDepartments() {
  try {
    const deptRes = await getDepartmentSimple()
    const list = deptRes.items || deptRes.data || deptRes || []
    departmentOptions.value = Array.isArray(list) ? list : []
  } catch { /* ignore */ }
}
async function fetchDocLevels() {
  try {
    const levelRes = await getDocLevels()
    if (levelRes && Array.isArray(levelRes.levels) && levelRes.levels.length > 0) {
      docLevels.value = levelRes.levels
    }
  } catch { /* ignore */ }
}
async function fetchOptions() {
  await fetchCategories()
  await fetchDepartments()
  await fetchDocLevels()
}

// 搜索/重置
function handleSearch() { fetchGroupedDocuments() }
function handleReset() {
  searchForm.keyword = ''; searchForm.category_id = ''; searchForm.department_id = ''; searchForm.doc_level = ''; searchForm.confidential_level = ''
  fetchGroupedDocuments()
}

async function handleGroupPageChange(groupId, page) {
  // 只更新当前组的页码和文档，其他组不动
  const group = categoryGroups.value.find(g => g.id === groupId)
  if (!group) return
  group._page = page
  try {
    const params = {
      keyword: searchForm.keyword || undefined,
      category_id: searchForm.category_id || undefined,
      department_id: searchForm.department_id || undefined,
      doc_level: searchForm.doc_level || undefined,
      confidential_level: searchForm.confidential_level || undefined,
      page,
      page_size: 30,
    }
    const res = await getDocumentGrouped(params)
    const targetGroup = (res || []).find(g => g.id === groupId)
    if (targetGroup) {
      group.documents = targetGroup.documents
      group.total = targetGroup.total
    }
  } catch { /* ignore */ }
}

// 查看
async function handleView(row) {
  try {
    currentDoc.value = await getDocumentDetail(row.id)
    detailVisible.value = true
  } catch { /* ignore */ }
}

// 下载
async function handleDownload(row) {
  try {
    const res = await downloadDocument(row.id)
    const blob = res instanceof Blob ? res : new Blob([res])
    saveBlobAsFile(blob, row.file_name || row.title || '文档')
    ElMessage.success('下载成功')
  } catch { /* ignore */ }
}

// 从Blob错误响应中解析错误消息
async function parseBlobError(blob) {
  try {
    if (blob instanceof Blob && blob.type && blob.type.includes('application/json')) {
      const text = await blob.text()
      const data = JSON.parse(text)
      return data.detail || data.message || '预览失败'
    }
  } catch {}
  return '预览失败，请下载后查看'
}

// 预览
async function handlePreview(row) {
  if (!row.file_name) { ElMessage.warning('文件信息不完整，无法预览'); return }

  const ext = (row.file_name.split('.').pop() || '').toLowerCase()
  const token = localStorage.getItem('token') || ''

  // 重置预览状态
  previewErrorTitle.value = '无法预览'
  previewErrorMessage.value = '该文件格式暂不支持在线预览，请下载后查看'

  // 手机端：直接导航到 PDF/图片 URL，让手机浏览器自身阅读器渲染
  if (isMobile.value) {
    if (OFFICE_EXTS.includes(ext) || ext === 'pdf') {
      window.location.href = `/api/documents/${row.id}/preview.pdf?token=${encodeURIComponent(token)}`
      return
    }
    if (ext in IMAGE_MIME_MAP) {
      window.location.href = `/api/documents/${row.id}/download?inline=1&token=${encodeURIComponent(token)}`
      return
    }
    if (ext === 'txt' || ext === 'md') {
      previewLoading.value = true; previewError.value = false; previewUnsupported.value = false
      previewVisible.value = true
      try {
        const res = await downloadDocument(row.id)
        previewText.value = await res.text()
        previewType.value = 'txt'
      } catch { previewError.value = true }
      finally { previewLoading.value = false }
      return
    }
    ElMessage.warning('手机端暂不支持预览该文件格式')
    return
  }

  // PC 端：内嵌预览
  previewLoading.value = true; previewError.value = false; previewUnsupported.value = false; previewVisible.value = true
  try {
    if (OFFICE_EXTS.includes(ext) || ext === 'pdf') {
      try {
        const pdfRes = await request.get(`/documents/${row.id}/preview-pdf`, { responseType: 'blob' })
        // 检查返回的是否是错误JSON（HTTP 200但内容是JSON错误）
        if (pdfRes instanceof Blob && pdfRes.type && pdfRes.type.includes('application/json')) {
          const errMsg = await parseBlobError(pdfRes)
          throw new Error(errMsg)
        }
        const pdfBlob = pdfRes instanceof Blob ? pdfRes : new Blob([pdfRes], { type: 'application/pdf' })
        previewUrl.value = URL.createObjectURL(pdfBlob)
        previewType.value = 'pdf'
        // 预览成功后再上报日志
        reportPreviewLog(row.id).catch(() => {})
      } catch (err) {
        const errMsg = err?.errorMessage || err?.message || '预览失败，请下载后查看'
        previewErrorTitle.value = '无法在线预览'
        previewErrorMessage.value = errMsg
        previewUnsupported.value = true
        previewDownloadRow.value = row
      }
    } else if (ext === 'txt' || ext === 'md') {
      const res = await downloadDocument(row.id)
      previewText.value = await res.text()
      previewUrl.value = URL.createObjectURL(new Blob([res], { type: 'text/plain;charset=utf-8' }))
      previewType.value = 'txt'
      // 预览成功后再上报日志
      reportPreviewLog(row.id).catch(() => {})
    } else if (ext in IMAGE_MIME_MAP) {
      const res = await downloadDocument(row.id)
      const imgBlob = res instanceof Blob ? res : new Blob([res], { type: IMAGE_MIME_MAP[ext] || 'image/png' })
      previewUrl.value = URL.createObjectURL(imgBlob)
      previewType.value = 'image'
      // 预览成功后再上报日志
      reportPreviewLog(row.id).catch(() => {})
    } else {
      previewUnsupported.value = true
      previewDownloadRow.value = row
    }
  } catch (err) {
    previewError.value = true
    console.error('预览加载失败:', err)
  } finally { previewLoading.value = false }
}

// 删除
async function handleDelete(row) {
  try {
    await ElMessageBox.confirm(`确定要删除文档「${row.title}」吗？删除后文档将移至回收站，管理员可恢复。`, '删除确认', { confirmButtonText: '确定删除', cancelButtonText: '取消', type: 'warning' })
    await deleteDocument(row.id)
    ElMessage.success('删除成功'); fetchGroupedDocuments()
  } catch { /* ignore */ }
}

// 编辑
async function handleEdit(row) {
  try {
    const res = await getDocumentDetail(row.id)
    editDoc.value = res
    editForm.title = res.title || ''; editForm.doc_no = res.doc_no || ''; editForm.summary = res.summary || ''
    editForm.category_id = res.category_id || ''; editForm.department_id = res.department_id || ''
    editForm.doc_level = res.doc_level || '无级别'; editForm.confidential_level = res.confidential_level || ''
    editVisible.value = true
  } catch { /* ignore */ }
}
async function handleEditSubmit() {
  if (!editFormRef.value) return
  await editFormRef.value.validate(async (valid) => {
    if (!valid || !editDoc.value) return
    editSubmitting.value = true
    try {
      await updateDocument(editDoc.value.id, {
        title: editForm.title, summary: editForm.summary || undefined,
        category_id: editForm.category_id || undefined,
        department_id: editForm.department_id || undefined,
        doc_level: editForm.doc_level || undefined,
        confidential_level: editForm.confidential_level || undefined,
        doc_no: editForm.doc_no || undefined,
      })
      ElMessage.success('更新成功'); editVisible.value = false; fetchGroupedDocuments()
    } catch { /* ignore */ } finally { editSubmitting.value = false }
  })
}
function handleDownloadFromPreview() {
  if (previewDownloadRow.value) handleDownload(previewDownloadRow.value)
}

// ── 权限管理 ──

async function handlePermission(row) {
  permDoc.value = row; permVisible.value = true
  try {
    permList.value = await getDocPermissions(row.id)
  } catch { permList.value = [] }
  try {
    const roles = await getRoleList()
    roleOptions.value = roles
  } catch { roleOptions.value = [] }
}
async function searchUsers(keyword) {
  if (!keyword || keyword.length < 1) { userOptions.value = []; return }
  userSearchLoading.value = true
  try {
    const res = await getUserList({ keyword, page_size: 20 })
    userOptions.value = res.items || res.data || []
  } catch { userOptions.value = [] } finally { userSearchLoading.value = false }
}
async function handleGrantPerm() {
  if (!newPerm.user_id && !newPerm.role_id) { ElMessage.warning('请选择用户或角色'); return }
  permSaving.value = true
  try {
    await grantDocPermission(permDoc.value.id, {
      user_id: newPerm.user_id || null, role_id: newPerm.role_id || null,
      can_view: newPerm.can_view, can_download: newPerm.can_download, can_edit: newPerm.can_edit,
    })
    ElMessage.success('授权成功')
    permList.value = await getDocPermissions(permDoc.value.id)
    newPerm.user_id = null; newPerm.role_id = null; newPerm.can_view = true; newPerm.can_download = true; newPerm.can_edit = false
  } catch { /* ignore */ } finally { permSaving.value = false }
}
async function handleRevokePerm(permId) {
  try {
    await ElMessageBox.confirm('确定要撤销此权限吗？', '确认', { type: 'warning' })
    await revokeDocPermission(permId)
    ElMessage.success('权限已撤销')
    permList.value = await getDocPermissions(permDoc.value.id)
  } catch { /* ignore */ }
}

// ── 批量选择 ──

function handleSelectionChange(rows) { selectedDocs.value = rows }

function batchUserLabel(uid) { const u = batchUserMap.value[uid]; return u ? (u.display_name || u.username) : `#${uid}` }
function batchRoleLabel(rid) { return batchRoleMap.value[rid] || `#${rid}` }

async function handleBatchPerm() {
  batchPerm.dept_id = null; batchPerm.addUser = null; batchPerm.addRole = null
  batchPerm.user_ids = []; batchPerm.role_ids = []; batchUserMap.value = {}; batchRoleMap.value = {}
  batchPerm.can_view = true; batchPerm.can_download = true; batchPerm.can_edit = false
  batchPermVisible.value = true

  try {
    const res = await getDepartmentList({ page_size: 100 })
    deptOptions.value = res.items || res.data || []
  } catch { deptOptions.value = [] }
  try {
    roleOptions.value = await getRoleList()
    for (const r of roleOptions.value) batchRoleMap.value[r.id] = r.name
  } catch { roleOptions.value = [] }
}
async function handleDeptChange(deptId) {
  if (!deptId) return
  try {
    const res = await getUserList({ department_id: deptId, page_size: 500 })
    const users = res.items || res.data || []
    for (const u of users) {
      if (!batchPerm.user_ids.includes(u.id)) {
        batchPerm.user_ids.push(u.id)
        batchUserMap.value[u.id] = { username: u.username, display_name: u.display_name }
      }
    }
    ElMessage.success(`已添加 ${users.length} 名用户`)
  } catch { /* ignore */ }
  batchPerm.dept_id = null
}
function handleAddUser(uid) {
  if (!uid) return
  if (batchPerm.user_ids.includes(uid)) { ElMessage.warning('该用户已在列表中'); batchPerm.addUser = null; return }
  batchPerm.user_ids.push(uid)
  const u = userOptions.value.find(u => u.id === uid)
  if (u) batchUserMap.value[uid] = { username: u.username, display_name: u.display_name }
  batchPerm.addUser = null
}
function handleRemoveUser(uid) { batchPerm.user_ids = batchPerm.user_ids.filter(id => id !== uid) }
function handleAddRole(roleId) {
  if (!roleId) return
  if (batchPerm.role_ids.includes(roleId)) { ElMessage.warning('该角色已添加'); return }
  batchPerm.role_ids.push(roleId); batchPerm.addRole = null
}
function handleRemoveRole(rid) { batchPerm.role_ids = batchPerm.role_ids.filter(id => id !== rid) }

async function handleBatchPermSubmit() {
  if (batchPerm.user_ids.length === 0 && batchPerm.role_ids.length === 0) { ElMessage.warning('请至少添加一个用户或角色'); return }
  if (selectedDocs.value.length === 0) { ElMessage.warning('请先选择文档'); return }
  batchPermSaving.value = true
  try {
    const docIds = selectedDocs.value.map(d => d.id)
    await grantBatchDocPermission(docIds, {
      user_ids: batchPerm.user_ids, role_ids: batchPerm.role_ids,
      can_view: batchPerm.can_view, can_download: batchPerm.can_download, can_edit: batchPerm.can_edit,
    })
    ElMessage.success(`已为 ${batchPerm.user_ids.length} 个用户、${batchPerm.role_ids.length} 个角色对 ${docIds.length} 个文档批量授权`)
    batchPermVisible.value = false
  } catch { /* ignore */ } finally { batchPermSaving.value = false }
}

onMounted(() => { fetchGroupedDocuments(); fetchOptions() })
</script>

<style scoped>
.document-manage {
  display: flex;
  flex-direction: column;
  gap: 16px;
  max-width: 1400px;
  margin: 0 auto;
}

/* ── 搜索栏 ── */
.search-card {
  border-radius: 10px;
  background: #fff;
  position: relative;
}
.search-card :deep(.el-card__body) {
  padding: 16px 20px;
}
.search-form {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 4px;
}
.search-form .el-form-item {
  margin-bottom: 0;
}

/* ── 分组容器 ── */
.doc-groups {
  display: flex;
  flex-direction: column;
  gap: 16px;
  min-height: 200px;
}

/* ── 单个分类组 ── */
.doc-group {
  background: #fff;
  border-radius: 10px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.06);
  transition: box-shadow 0.2s;
  overflow: hidden;
}
.doc-group:hover {
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

/* ── 分类标题栏 ── */
.group-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 14px 20px;
  cursor: pointer;
  user-select: none;
  border-bottom: 1px solid #f0f0f0;
  transition: background 0.15s;
}
.group-header:hover {
  background: #f7f9fc;
}
.group-header-left {
  display: flex;
  align-items: center;
  gap: 8px;
}
.group-toggle-icon {
  font-size: 14px;
  color: #86909c;
  transition: transform 0.25s;
}
.group-toggle-icon.rotated {
  transform: rotate(0deg);
}
.group-folder-icon {
  font-size: 20px;
  color: #165dff;
}
.group-name {
  font-size: 16px;
  font-weight: 600;
  color: #1d2129;
}
.group-count {
  font-size: 12px;
}
.group-header-right {
  display: flex;
  align-items: center;
  gap: 6px;
}
.group-latest {
  font-size: 12px;
  color: #86909c;
}

/* ── 视图切换按钮 ── */
.view-toggle {
  position: absolute;
  right: 20px;
  top: 18px;
  display: flex;
  gap: 8px;
}

/* ── 文档卡片网格 ── */
.doc-cards {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 14px;
  padding: 18px 20px;
}
@media (max-width: 1200px) {
  .doc-cards { grid-template-columns: repeat(3, 1fr); }
}
@media (max-width: 900px) {
  .doc-cards { grid-template-columns: repeat(2, 1fr); }
}
@media (max-width: 600px) {
  .doc-cards { grid-template-columns: 1fr; }
}

/* ── 文档列表视图 ── */
.doc-list {
  padding: 12px 20px;
}
.list-file-name {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
}
.list-file-name:hover .list-title {
  color: #165dff;
}
.list-type-tag {
  flex-shrink: 0;
  min-width: 38px;
  text-align: center;
}
.list-title {
  font-size: 14px;
  color: #1d2129;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  transition: color 0.15s;
}

/* ── 单个文档卡片 ── */
.doc-card {
  position: relative;
  display: flex;
  flex-direction: column;
  background: #fafafa;
  border: 1px solid #f0f0f0;
  border-radius: 8px;
  padding: 14px;
  cursor: pointer;
  transition: all 0.2s ease;
}
.doc-card:hover {
  background: #fff;
  border-color: #d9e1ff;
  box-shadow: 0 4px 16px rgba(22, 93, 255, 0.10);
  transform: translateY(-2px);
}

/* ── 卡片顶部：文件类型图标 ── */
.card-top {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 10px;
}
.card-type-icon {
  width: 42px;
  height: 42px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 11px;
  font-weight: 700;
  color: #fff;
  flex-shrink: 0;
}
.type-text {
  line-height: 1;
}
.card-type-icon.type-pdf { background: linear-gradient(135deg, #f5222d, #cf1322); }
.card-type-icon.type-doc,
.card-type-icon.type-docx { background: linear-gradient(135deg, #2b6df6, #165dff); }
.card-type-icon.type-xls,
.card-type-icon.type-xlsx { background: linear-gradient(135deg, #389e0d, #237804); }
.card-type-icon.type-ppt,
.card-type-icon.type-pptx { background: linear-gradient(135deg, #d46b08, #c43800); }
.card-type-icon.type-png,
.card-type-icon.type-jpg,
.card-type-icon.type-jpeg,
.card-type-icon.type-gif,
.card-type-icon.type-webp { background: linear-gradient(135deg, #722ed1, #531dab); }
.card-type-icon.type-txt,
.card-type-icon.type-md { background: linear-gradient(135deg, #5c6670, #434a54); }
.card-type-icon.type-unknown { background: linear-gradient(135deg, #86909c, #6b7785); }

.card-conf-level {
  flex-shrink: 0;
  margin-left: auto;
}

/* ── 文档标题 ── */
.card-title {
  font-size: 14px;
  font-weight: 600;
  color: #1d2129;
  line-height: 1.4;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  margin-bottom: 6px;
  min-height: 40px;
}

/* ── 文档编号 ── */
.card-doc-no {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  color: #86909c;
  margin-bottom: 8px;
}
.card-doc-no .el-icon {
  font-size: 13px;
}

/* 卡片部门/级别标签 */
.card-dep-level {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 8px;
  min-height: 22px;
}

/* ── 底部信息 ── */
.card-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 12px;
  color: #86909c;
  margin-top: auto;
  padding-top: 8px;
  border-top: 1px solid #f0f0f0;
}
.card-meta,
.card-uploader {
  display: flex;
  align-items: center;
  gap: 4px;
}
.card-meta .el-icon,
.card-uploader .el-icon {
  font-size: 13px;
}

/* ── 悬浮操作栏 ── */
.card-actions {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 0;
  flex-wrap: nowrap;
  padding: 6px 4px;
  background: rgba(255, 255, 255, 0.95);
  border-radius: 0 0 8px 8px;
  backdrop-filter: blur(4px);
  opacity: 0;
  pointer-events: none;
  transition: opacity 0.2s ease;
  border-top: 1px solid #e8e8e8;
  white-space: nowrap;
  overflow: hidden;
}
.card-actions .el-button {
  padding: 4px 6px !important;
  font-size: 12px !important;
  flex-shrink: 0;
}
.doc-card:hover .card-actions {
  opacity: 1;
  pointer-events: auto;
}

/* ── 预览对话框 ── */
.preview-iframe { width: 100%; height: calc(100vh - 120px); border: none; }
.preview-loading { padding: 40px; }
.preview-error { padding: 80px 0; }
.preview-unsupported { display: flex; justify-content: center; align-items: center; min-height: 400px; }
.preview-txt { padding: 20px; max-height: calc(100vh - 120px); overflow-y: auto; background: #f7f8fa; }
.preview-txt pre { margin: 0; white-space: pre-wrap; word-wrap: break-word; font-size: 14px; line-height: 1.6; }
.preview-image { display: flex; justify-content: center; align-items: center; min-height: calc(100vh - 160px); padding: 20px; background: #f7f8fa; overflow: auto; }
.preview-img { max-width: 100%; max-height: calc(100vh - 200px); object-fit: contain; border-radius: 4px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }

/* ── 权限对话框 ── */
.perm-header { display: flex; align-items: center; gap: 6px; margin-bottom: 16px; padding: 8px 12px; background: #f7f8fa; border-radius: 6px; }
.perm-section-title { display: flex; align-items: center; gap: 6px; font-size: 14px; font-weight: 600; color: #1d2129; margin: 12px 0 10px; }
.perm-form { display: flex; flex-wrap: wrap; align-items: flex-start; gap: 4px; }
.batch-perm-content { padding: 4px 0; }
.batch-perm-info { display: flex; align-items: center; gap: 8px; margin-bottom: 12px; padding: 8px 12px; background: #fff7e6; border-radius: 6px; font-size: 13px; color: #d46b08; }
.batch-user-section, .batch-role-section { margin-bottom: 8px; }
.batch-tags { display: flex; align-items: flex-start; flex-wrap: wrap; gap: 4px; padding: 6px 0; }
.batch-tags-label { font-size: 13px; color: #606266; flex-shrink: 0; line-height: 24px; min-width: 70px; }

/* ── 组内分页 ── */
.group-pagination {
  display: flex;
  justify-content: center;
  padding: 12px 20px 16px;
  border-top: 1px solid #f0f0f0;
}
</style>
