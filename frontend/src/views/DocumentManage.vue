<template>
  <div class="document-manage">
    <!-- 左侧：分类目录树（宽度可拖动） -->
    <aside
      class="category-sidebar"
      :class="{ 'is-collapsed': sidebarCollapsed, 'is-resizing': isResizing }"
      :style="sidebarCollapsed ? undefined : { width: sidebarWidth + 'px' }"
    >
      <div
        v-show="!sidebarCollapsed && !isMobile"
        class="sidebar-resizer"
        title="拖动调整宽度，双击恢复默认"
        @pointerdown="startResize"
        @dblclick="resetSidebarWidth"
      />
      <div class="sidebar-header">
        <span class="sidebar-title">文档分类</span>
        <el-tooltip :content="sidebarCollapsed ? '展开侧边栏' : '收起侧边栏'" placement="top">
          <el-button link :icon="sidebarCollapsed ? Expand : Fold" @click="sidebarCollapsed = !sidebarCollapsed" />
        </el-tooltip>
      </div>

      <el-scrollbar v-show="!sidebarCollapsed" class="sidebar-scroll">
        <div
          class="tree-node tree-all"
          :class="{ active: selectedCategoryId === null }"
          @click="selectCategory(null)"
        >
          <el-icon class="tree-icon"><Files /></el-icon>
          <span class="tree-label">全部分类</span>
          <span class="tree-count">{{ totalDocCount }}</span>
        </div>

        <el-tree
          ref="categoryTreeRef"
          :data="categoryTree"
          node-key="id"
          :props="{ label: 'name', children: 'children' }"
          :expand-on-click-node="false"
          :default-expanded-keys="expandedCategoryKeys"
          highlight-current
          @node-click="handleCategoryClick"
        >
          <template #default="{ data }">
            <span class="tree-node" :class="{ active: selectedCategoryId === data.id }">
              <el-icon class="tree-icon">
                <FolderOpened v-if="data.children && data.children.length" />
                <Document v-else />
              </el-icon>
              <span class="tree-label" :title="data.path">{{ data.name }}</span>
              <span class="tree-count">{{ data.subtree_doc_count ?? data.doc_count }}</span>
            </span>
          </template>
        </el-tree>

        <div
          class="tree-node tree-uncat"
          :class="{ active: selectedCategoryId === UNCATEGORIZED }"
          @click="selectCategory(UNCATEGORIZED)"
        >
          <el-icon class="tree-icon"><FolderDelete /></el-icon>
          <span class="tree-label">未分类</span>
          <span class="tree-count">{{ uncategorizedCount }}</span>
        </div>
      </el-scrollbar>
    </aside>

    <!-- 右侧：文档列表 -->
    <div class="doc-pane">
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

    <!-- 当前分类下的文档 -->
    <div class="doc-list-area" v-loading="loading">
      <div class="list-toolbar">
        <span class="current-category">
          <el-icon><FolderOpened /></el-icon>
          {{ currentCategoryLabel }}
        </span>
        <span class="doc-total">共 {{ pagination.total }} 篇</span>
      </div>

      <template v-if="documents.length > 0">
        <!-- 文档卡片网格 -->
        <div v-if="viewMode === 'card'" class="doc-cards">
          <div
            v-for="doc in documents"
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
                <div class="card-title" :title="doc.title">
                  {{ doc.title }}
                  <el-tag
                    v-if="doc.version > 1 || doc.version_total > 1"
                    size="small"
                    type="warning"
                    effect="plain"
                    class="card-version-tag"
                  >v{{ doc.version }}</el-tag>
                </div>

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
                    <el-tag v-if="doc.is_expired" size="small" type="danger" effect="plain" style="margin-left:4px">已过期</el-tag>
                  </div>
                  <div class="card-uploader" v-if="doc.uploader">
                    <el-icon><User /></el-icon>
                    <span>{{ doc.uploader.display_name || doc.uploader.username }}</span>
                  </div>
                </div>

                <!-- 悬浮操作栏 -->
                <div class="card-actions" @click.stop>
                  <el-button type="primary" link size="small" @click.stop="handleView(doc)">查看</el-button>
                  <el-button v-if="doc.version_total > 1" type="warning" link size="small" @click.stop="handleVersions(doc)">
                    {{ doc.version_total }}个版本
                  </el-button>
                  <el-button v-if="canEdit" type="warning" link size="small" @click.stop="handleEdit(doc)">编辑</el-button>
                  <el-button v-if="doc.can_download !== false" type="success" link size="small" @click.stop="handleDownload(doc)">下载</el-button>
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

        <!-- 文档列表视图 -->
        <div v-if="viewMode === 'list'" class="doc-list">
          <el-table :data="documents" stripe size="small" style="width: 100%">
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
                      <el-tag
                        v-if="row.version > 1 || row.version_total > 1"
                        size="small"
                        type="warning"
                        effect="plain"
                        class="list-version-tag"
                      >v{{ row.version }}</el-tag>
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
                    <el-tag v-if="row.is_expired" size="small" type="danger" effect="plain" style="margin-left:2px">过期</el-tag>
                  </template>
                </el-table-column>
                <el-table-column label="操作" :width="opColumnWidth" fixed="right">
                  <template #default="{ row }">
                    <div class="table-op-btns">
                    <el-button type="primary" link size="small" @click.stop="handleView(row)">查看</el-button>
                    <el-button v-if="row.version_total > 1" type="warning" link size="small" @click.stop="handleVersions(row)">
                      {{ row.version_total }}个版本
                    </el-button>
                    <el-button v-if="canEdit" type="warning" link size="small" @click.stop="handleEdit(row)">编辑</el-button>
                    <el-button v-if="row.can_download !== false" type="success" link size="small" @click.stop="handleDownload(row)">下载</el-button>
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

        <!-- 分页 -->
        <div class="list-pagination">
          <el-pagination
            v-model:current-page="pagination.page"
            v-model:page-size="pagination.pageSize"
            :total="pagination.total"
            :page-sizes="[12, 24, 48, 96]"
            layout="total, sizes, prev, pager, next, jumper"
            background
            @size-change="handlePageSizeChange"
            @current-change="handlePageChange"
          />
        </div>
      </template>

      <!-- 空状态 -->
      <el-empty v-else-if="!loading" description="该分类下暂无符合条件的文档">
        <template #image>
          <el-icon :size="60" color="#c0c4cc"><FolderDelete /></el-icon>
        </template>
        <el-button v-if="canUpload" type="primary" :icon="Upload" @click="$router.push('/documents/upload')">
          上传文档
        </el-button>
      </el-empty>
    </div>
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
        <el-descriptions-item label="上传时间">
          {{ currentDoc.created_at }}
          <el-tag v-if="currentDoc.is_expired" size="small" type="danger" effect="plain" style="margin-left:4px">已过期</el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="文件大小">{{ formatFileSize(currentDoc.file_size) }}</el-descriptions-item>
        <el-descriptions-item label="文件格式">{{ currentDoc.file_type || '-' }}</el-descriptions-item>
        <el-descriptions-item label="文档描述" :span="2">{{ currentDoc.summary || '无' }}</el-descriptions-item>
      </el-descriptions>
      <template #footer>
        <el-button @click="detailVisible = false">关闭</el-button>
        <el-button v-if="currentDoc.can_download !== false" type="success" @click="handleDownload(currentDoc)">下载文档</el-button>
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
            <el-option v-for="item in categoryOptions" :key="item.id" :label="categoryOptionLabel(item)" :value="item.id" />
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

    <!-- 版本历史对话框 -->
    <el-dialog
      v-model="versionVisible"
      title="版本历史"
      width="760px"
      destroy-on-close
      draggable
    >
      <div v-if="versionDoc" class="version-header">
        <el-icon :size="16" color="#165dff"><Document /></el-icon>
        <strong>{{ versionDoc.title }}</strong>
        <span style="color:#86909c;font-size:12px">
          （{{ versionItems.length > 0 ? `共 ${versionItems[0].version_total || versionItems.length} 个版本` : '暂无版本信息' }}）
        </span>
      </div>
      <el-table
        v-loading="versionLoading"
        :data="versionItems"
        border
        size="small"
        style="margin-top:12px"
        max-height="380"
      >
        <el-table-column label="版本" width="76" align="center">
          <template #default="{ row }">
            <el-tag :type="row.is_current ? 'success' : 'info'" size="small" effect="plain">
              v{{ row.version }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="标题" min-width="180" show-overflow-tooltip>
          <template #default="{ row }">{{ row.title }}</template>
        </el-table-column>
        <el-table-column label="上传人" width="110">
          <template #default="{ row }">{{ row.uploader?.display_name || row.uploader?.username || '-' }}</template>
        </el-table-column>
        <el-table-column label="上传时间" width="130" header-align="center">
          <template #default="{ row }">{{ formatDate(row.created_at) }}</template>
        </el-table-column>
        <el-table-column label="当前" width="64" align="center">
          <template #default="{ row }">
            <el-tag v-if="row.is_current" type="success" size="small">当前</el-tag>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="220" fixed="right">
          <template #default="{ row }">
            <el-button v-if="row.can_view" type="primary" link size="small" @click="handleView(row)">查看</el-button>
            <el-button
              v-if="row.can_download && row.can_view"
              type="success"
              link
              size="small"
              @click="handleDownload(row)"
            >下载</el-button>
            <el-button
              v-if="canEdit && !row.is_current && row.can_view"
              type="warning"
              link
              size="small"
              @click="handleRollback(row)"
            >设为当前</el-button>
            <el-button
              v-if="canDeleteVersion && !row.is_current && row.can_view"
              type="danger"
              link
              size="small"
              @click="handleDeleteVersion(row)"
            >删除</el-button>
          </template>
        </el-table-column>
      </el-table>
      <template #footer>
        <el-button type="primary" @click="versionVisible = false">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, onUnmounted, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  Search, Refresh, Upload, Document, Setting, WarningFilled, ArrowDown,
  FolderOpened, FolderDelete, Clock, Grid, List, User, Files, Expand, Fold
} from '@element-plus/icons-vue'
import {
  getDocumentList, getDocumentDetail, downloadDocument, deleteDocument,
  updateDocument, reportPreviewLog, getDocPermissions, grantDocPermission,
  revokeDocPermission, getDocLevels, getDocumentVersions, rollbackDocumentVersion
} from '../api/document.js'
import { getCategoryListSimple } from '../api/category.js'
import { categoryOptionLabel } from '../utils/category.js'
import { getDepartmentSimple } from '../api/department.js'
import { getUserList } from '../api/user.js'
import { getRoleList } from '../api/role.js'
import { canUploadDoc, canModifyDoc, canDeleteDoc, canManageDocPermissions, canDeleteDocVersion } from '../utils/permission.js'
import { isPreviewable, getPreviewType, OFFICE_EXTS, IMAGE_MIME_MAP } from '../utils/preview.js'
import { saveBlobAsFile } from '../utils/download.js'
import { formatDate, formatFileSize, fileTypeTagType, confidentialityTagType, confidentialityLabel } from '../utils/format.js'
import { useMobile } from '../composables/useMobile.js'
import request from '../api/request.js'

const loading = ref(false)

// ── 分类目录树（左侧栏）──
const UNCATEGORIZED = '__uncat__'
const categoryTree = ref([])
const categoryTreeRef = ref(null)
const uncategorizedCount = ref(0)
const totalDocCount = ref(0)
// null = 全部分类；UNCATEGORIZED = 未分类；数字 = 具体分类ID
const selectedCategoryId = ref(null)
const sidebarCollapsed = ref(false)
const expandedCategoryKeys = ref([])

// ── 当前分类下的文档列表 ──
const documents = ref([])
const pagination = reactive({ page: 1, pageSize: 12, total: 0 })

// 视图模式：card / list，持久化到 localStorage
const VIEW_MODE_KEY = 'docmanage_view_mode'
const viewMode = ref(localStorage.getItem(VIEW_MODE_KEY) || 'card')
function setViewMode(mode) {
  viewMode.value = mode
  localStorage.setItem(VIEW_MODE_KEY, mode)
}

// 移动端检测（使用公共 composable）
const { isMobile } = useMobile()

// 侧边栏宽度可拖动调整，并记忆上次宽度
const SIDEBAR_WIDTH_KEY = 'docmanage_sidebar_width'
const SIDEBAR_DEFAULT_WIDTH = 240
const SIDEBAR_MAX_WIDTH = 520
// 最小宽度按「至少能看清 4 个汉字」推算：固定占用 + 4 字宽 + 树的最深缩进
const SIDEBAR_MIN_CHARS = 4
const SIDEBAR_CHAR_PX = 13      // 侧边栏字号 13px，一个汉字约 13px
const SIDEBAR_CHROME_PX = 104   // 内边距 + 文件夹图标 + 间距 + 数量徽标（含三位数）+ 滚动条余量
const TREE_INDENT_PX = 16       // el-tree 每层缩进

const sidebarWidth = ref(Number(localStorage.getItem(SIDEBAR_WIDTH_KEY)) || SIDEBAR_DEFAULT_WIDTH)
const isResizing = ref(false)
let resizeStartX = 0
let resizeStartWidth = 0

/** 分类树的最大层级深度（用于把缩进算进最小宽度） */
function maxTreeDepth(nodes, depth = 0) {
  let max = depth
  for (const node of nodes || []) {
    const children = node.children || []
    if (children.length) max = Math.max(max, maxTreeDepth(children, depth + 1))
  }
  return max
}

/** 侧边栏最小宽度：保证分类名至少显示 4 个汉字 */
const minSidebarWidth = computed(() =>
  SIDEBAR_CHROME_PX + SIDEBAR_CHAR_PX * SIDEBAR_MIN_CHARS + maxTreeDepth(categoryTree.value) * TREE_INDENT_PX
)

/** 最大宽度：右侧文档区至少保留 420px，避免把列表挤没 */
function maxSidebarWidth() {
  const available = window.innerWidth - 420
  return Math.max(minSidebarWidth.value, Math.min(SIDEBAR_MAX_WIDTH, available))
}

function clampSidebarWidth(value) {
  return Math.min(Math.max(value, minSidebarWidth.value), maxSidebarWidth())
}

function startResize(event) {
  if (event.button > 0) return
  event.preventDefault()
  isResizing.value = true
  resizeStartX = event.clientX
  resizeStartWidth = sidebarWidth.value
  document.body.style.cursor = 'col-resize'
  document.body.style.userSelect = 'none'
  window.addEventListener('pointermove', handleResizeMove)
  window.addEventListener('pointerup', stopResize)
}

function handleResizeMove(event) {
  if (!isResizing.value) return
  sidebarWidth.value = clampSidebarWidth(resizeStartWidth + (event.clientX - resizeStartX))
}

function stopResize() {
  if (!isResizing.value) return
  isResizing.value = false
  document.body.style.cursor = ''
  document.body.style.userSelect = ''
  window.removeEventListener('pointermove', handleResizeMove)
  window.removeEventListener('pointerup', stopResize)
  localStorage.setItem(SIDEBAR_WIDTH_KEY, String(sidebarWidth.value))
}

function resetSidebarWidth() {
  sidebarWidth.value = clampSidebarWidth(SIDEBAR_DEFAULT_WIDTH)
  localStorage.setItem(SIDEBAR_WIDTH_KEY, String(sidebarWidth.value))
}

/** 窗口尺寸变化时收窄过大的侧边栏，保证文档列表可见 */
function handleWindowResize() {
  if (!isResizing.value) sidebarWidth.value = clampSidebarWidth(sidebarWidth.value)
}

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

// 版本历史
const versionVisible = ref(false)
const versionLoading = ref(false)
const versionDoc = ref(null)
const versionItems = ref([])

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
const canDeleteVersion = computed(() => canDeleteDocVersion())
const canEdit = computed(() => canModifyDoc())
const canManagePermissions = computed(() => canManageDocPermissions())

// 操作列宽度：按当前用户权限的按钮数量动态估算，使各角色的列都贴合内容、避免留白
const opColumnWidth = computed(() => {
  const btnW = (len) => len * 14 + 16 // 中文按钮按 14px/字 + 内边距估算
  const gap = 8
  const pad = 26
  const texts = []
  texts.push('查看')
  texts.push('9个版本') // 版本按钮按最宽文本占位，避免截断
  if (canEdit.value) texts.push('编辑')
  if (canDelete.value) texts.push('删除')
  texts.push('下载')
  texts.push('预览')
  if (canManagePermissions.value) texts.push('权限')
  let w = pad
  texts.forEach((t, i) => { w += btnW(t.length) + (i > 0 ? gap : 0) })
  return Math.max(170, Math.min(320, Math.round(w)))
})

// ── 数据加载 ──

/** 加载当前选中分类下的文档（右侧列表） */
async function fetchDocuments() {
  loading.value = true
  try {
    const params = {
      keyword: searchForm.keyword || undefined,
      department_id: searchForm.department_id || undefined,
      doc_level: searchForm.doc_level || undefined,
      confidential_level: searchForm.confidential_level || undefined,
      page: pagination.page,
      page_size: pagination.pageSize,
    }
    // 分类筛选来自左侧目录树：选具体分类时带 category_id（后端含其子分类）
    if (typeof selectedCategoryId.value === 'number') {
      params.category_id = selectedCategoryId.value
    }
    const res = await getDocumentList(params)
    let items = res.items || res.data || []
    // 「未分类」在前端过滤（后端没有专门的未分类查询参数）
    if (selectedCategoryId.value === UNCATEGORIZED) {
      items = items.filter(d => d.category_id == null && !d.category)
    }
    documents.value = items
    pagination.total = selectedCategoryId.value === UNCATEGORIZED ? items.length : (res.total || 0)
  } catch { /* ignore */ } finally { loading.value = false }
}

/** 加载分类目录树 + 各分类文档数（左侧栏数据源） */
async function fetchCategoryTree() {
  try {
    const res = await getCategoryListSimple()
    categoryOptions.value = res.items || res.data || res || []
    categoryTree.value = Array.isArray(res.tree) ? res.tree : []
    uncategorizedCount.value = res.uncategorized_count || 0
    totalDocCount.value = (res.items || []).reduce((sum, c) => sum + (c.doc_count || 0), 0) + uncategorizedCount.value
    // 默认展开一级分类
    expandedCategoryKeys.value = categoryTree.value.map(n => n.id)
    // 分类树加载后按最新层级修正宽度，保证至少能显示 4 个汉字
    sidebarWidth.value = clampSidebarWidth(sidebarWidth.value)
  } catch { /* ignore */ }
}

/** 点击左侧树节点：选中该分类，并保持/展开其子分类 */
function handleCategoryClick(data, node) {
  selectCategory(data.id)
  if (node && Array.isArray(node.childNodes) && node.childNodes.length && !node.expanded) {
    node.expand()
  }
}

function selectCategory(id) {
  const next = (id === UNCATEGORIZED) ? UNCATEGORIZED : (id ?? null)
  if (next === selectedCategoryId.value) return
  selectedCategoryId.value = next
  pagination.page = 1
  fetchDocuments()
}

/** 当前分类的面包屑文字 */
const currentCategoryLabel = computed(() => {
  if (selectedCategoryId.value === null) return '全部分类'
  if (selectedCategoryId.value === UNCATEGORIZED) return '未分类'
  const find = (nodes) => {
    for (const n of nodes || []) {
      if (n.id === selectedCategoryId.value) return n
      const hit = find(n.children || [])
      if (hit) return hit
    }
    return null
  }
  const node = find(categoryTree.value)
  return node ? (node.path || node.name) : '分类'
})

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
  await fetchCategoryTree()
  await fetchDepartments()
  await fetchDocLevels()
}

// 搜索/重置
function handleSearch() {
  pagination.page = 1
  fetchDocuments()
}
function handleReset() {
  searchForm.keyword = ''; searchForm.department_id = ''; searchForm.doc_level = ''; searchForm.confidential_level = ''
  pagination.page = 1
  fetchDocuments()
}

function handlePageChange(page) {
  pagination.page = page
  fetchDocuments()
}

function handlePageSizeChange(size) {
  pagination.pageSize = size
  pagination.page = 1
  fetchDocuments()
}

// 查看
async function handleView(row) {
  try {
    currentDoc.value = await getDocumentDetail(row.id)
    detailVisible.value = true
  } catch { /* ignore */ }
}

// 版本历史
async function handleVersions(row) {
  versionDoc.value = row
  versionItems.value = []
  versionVisible.value = true
  versionLoading.value = true
  try {
    const res = await getDocumentVersions(row.id)
    versionItems.value = (res && res.items) || []
  } catch { versionItems.value = [] } finally { versionLoading.value = false }
}

async function handleRollback(row) {
  if (!versionDoc.value) return
  try {
    await ElMessageBox.confirm(
      `确定要将该文档回滚到 v${row.version} 吗？回滚后该版本将成为当前可见版本，不影响历史版本。`,
      '回滚确认',
      { confirmButtonText: '确认回滚', cancelButtonText: '取消', type: 'warning' }
    )
    await rollbackDocumentVersion(versionDoc.value.id, row.version)
    ElMessage.success(`已回滚到 v${row.version}`)
    versionVisible.value = false
    fetchDocuments()
  } catch { /* ignore */ }
}

// 删除旧版本：软删除该版本记录，其余版本不受影响
async function handleDeleteVersion(row) {
  if (!versionDoc.value) return
  try {
    await ElMessageBox.confirm(
      `确定要删除 v${row.version} 这个历史版本吗？删除后该版本将从版本历史中移除（可到回收站恢复），不影响其他版本。`,
      '删除版本确认',
      { confirmButtonText: '确认删除', cancelButtonText: '取消', type: 'warning' }
    )
    await deleteDocument(row.id)
    ElMessage.success(`已删除 v${row.version}`)
    // 刷新版本历史：若当前文档本身被删除则关闭面板
    const res = await getDocumentVersions(versionDoc.value.id)
    versionItems.value = (res && res.items) || []
    if (versionItems.value.length === 0) {
      versionVisible.value = false
    }
    fetchDocuments()
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
    ElMessage.success('删除成功'); fetchDocuments()
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
      ElMessage.success('更新成功'); editVisible.value = false; fetchDocuments()
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

onMounted(() => {
  // 窄屏默认收起侧边栏，给文档列表留出空间
  if (isMobile.value) sidebarCollapsed.value = true
  window.addEventListener('resize', handleWindowResize)
  fetchOptions()
  fetchDocuments()
})

onUnmounted(() => {
  window.removeEventListener('resize', handleWindowResize)
  window.removeEventListener('pointermove', handleResizeMove)
  window.removeEventListener('pointerup', stopResize)
  document.body.style.cursor = ''
  document.body.style.userSelect = ''
})
</script>

<style scoped>
.document-manage {
  display: flex;
  flex-direction: row;
  align-items: flex-start;
  gap: 16px;
  max-width: 1400px;
  margin: 0 auto;
}

/* ── 左侧分类目录树 ── */
.category-sidebar {
  width: 240px;
  flex-shrink: 0;
  background: #fff;
  border: 1px solid #e5e6eb;
  border-radius: 8px;
  display: flex;
  flex-direction: column;
  max-height: calc(100vh - 120px);
  position: sticky;
  top: 12px;
  overflow: hidden;
}

.category-sidebar.is-collapsed {
  width: 44px;
}

/* 右侧拖拽调宽手柄 */
.sidebar-resizer {
  position: absolute;
  top: 0;
  right: 0;
  width: 6px;
  height: 100%;
  cursor: col-resize;
  z-index: 5;
  touch-action: none;
}

.sidebar-resizer::after {
  content: '';
  position: absolute;
  top: 50%;
  right: 2px;
  width: 2px;
  height: 34px;
  transform: translateY(-50%);
  border-radius: 1px;
  background: #c9cdd4;
  opacity: 0;
  transition: opacity 0.15s;
}

.sidebar-resizer:hover::after,
.category-sidebar.is-resizing .sidebar-resizer::after {
  opacity: 1;
  background: #165dff;
}

.category-sidebar.is-resizing {
  user-select: none;
}

.category-sidebar.is-resizing :deep(.el-tree) {
  pointer-events: none;
}

.sidebar-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 12px;
  border-bottom: 1px solid #f0f0f0;
  flex-shrink: 0;
}

.sidebar-title {
  font-size: 14px;
  font-weight: 600;
  color: #1d2129;
  white-space: nowrap;
}

.category-sidebar.is-collapsed .sidebar-title {
  display: none;
}

.sidebar-scroll {
  flex: 1;
  min-height: 0;
  padding: 6px 0 10px;
}

.tree-node {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 5px 10px;
  border-radius: 6px;
  cursor: pointer;
  font-size: 13px;
  color: #4e5969;
  transition: background 0.15s, color 0.15s;
}

.tree-node:hover {
  background: #f2f3f5;
}

.tree-node.active {
  background: #e8f3ff;
  color: #165dff;
  font-weight: 500;
}

.tree-icon {
  font-size: 14px;
  color: #ffb400;
  flex-shrink: 0;
}

.tree-node.active .tree-icon {
  color: #165dff;
}

.tree-label {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.tree-count {
  flex-shrink: 0;
  min-width: 20px;
  padding: 0 6px;
  font-size: 12px;
  line-height: 18px;
  text-align: center;
  color: #86909c;
  background: #f2f3f5;
  border-radius: 9px;
}

.tree-node.active .tree-count {
  color: #165dff;
  background: #d4e8ff;
}

.tree-all,
.tree-uncat {
  margin: 2px 8px;
}

.category-sidebar :deep(.el-tree) {
  padding: 0 8px;
  background: transparent;
}

.category-sidebar :deep(.el-tree-node__content) {
  height: 32px;
  background: transparent;
}

.category-sidebar :deep(.el-tree-node__content:hover) {
  background: transparent;
}

/* ── 右侧文档区 ── */
.doc-pane {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.doc-list-area {
  min-height: 320px;
  display: flex;
  flex-direction: column;
}

.list-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 4px 10px;
}

.current-category {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 14px;
  font-weight: 600;
  color: #1d2129;
}

.doc-total {
  font-size: 12px;
  color: #86909c;
}

.list-pagination {
  display: flex;
  justify-content: flex-end;
  margin-top: 12px;
}

/* ── 搜索栏 ── */
.search-card {
  border-radius: 10px;
  background: #fff;
  position: relative;
}
.search-card :deep(.el-card__body) {
  padding: 16px 20px;
  overflow: visible;
}

/* 列表操作按钮：右对齐紧凑排列，避免在狭小列内被截断 */
.table-op-btns {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  white-space: nowrap;
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
.list-version-tag {
  flex-shrink: 0;
  margin-left: auto;
}

/* ── 版本历史 ── */
.version-header {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 4px;
  padding: 8px 12px;
  background: #f7f8fa;
  border-radius: 6px;
}
.card-version-tag {
  flex-shrink: 0;
  margin-left: 4px;
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
