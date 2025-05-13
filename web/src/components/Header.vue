<template>
  <div class="header-container">
    <div class="header">
      <div class="logo-section">
        <h1 class="logo">写字机</h1>
      </div>
      <div class="nav-section">
        <ul class="nav-menu">
          <li class="nav-item active"><router-link to="/">首页</router-link></li>
          <li class="nav-item"><router-link to="/docs">文档说明</router-link></li>
          <li class="nav-item"><router-link to="/contact">联系我们</router-link></li>
        </ul>
      </div>
      <div class="user-info">
        <el-button link size="small">登录</el-button>
        <span class="divider">|</span>
        <el-button link size="small">注册</el-button>
      </div>
    </div>
  </div>
</template>
  
<script>
export default {
  name: 'HeaderComponent'
}
</script>
  
<style scoped>
.header-container {
  width: 100%;
  background-color: #fff;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
  position: fixed;
  top: 0;
  left: 0;
  z-index: 1000;
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0 20px;
  height: 60px;
  max-width: 1200px;
  margin: 0 auto;
}

.logo-section {
  display: flex;
  align-items: center;
}

.logo {
  font-size: 24px;
  color: #0064c8;
  margin: 0;
  font-weight: 600;
}

.nav-section {
  flex: 1;
  display: flex;
  justify-content: center;
}

.nav-menu {
  display: flex;
  list-style: none;
  margin: 0;
  padding: 0;
}

.nav-item {
  margin: 0 20px;
  position: relative;
}

.nav-item a {
  text-decoration: none;
  color: #333;
  font-size: 16px;
  padding: 20px 0;
  display: block;
  transition: color 0.3s;
}

.nav-item a:hover {
  color: #0064c8;
}

.nav-item.active a {
  color: #0064c8;
  font-weight: 500;
}

.nav-item.active::after {
  content: '';
  position: absolute;
  bottom: -1px;
  left: 0;
  width: 100%;
  height: 2px;
  background-color: #0064c8;
}

.user-info {
  display: flex;
  align-items: center;
}

.divider {
  margin: 0 5px;
  color: #ddd;
}

/* Replace the deprecated button text styles with link button styles */
.el-button.is-link {
  color: #666;
  font-size: 14px;
}

.el-button.is-link:hover {
  color: #0064c8;
}

/* Remove the deprecated styles */
/* .el-button--text {
  color: #666;
  font-size: 14px;
}

.el-button--text:hover {
  color: #0064c8;
} */
</style>