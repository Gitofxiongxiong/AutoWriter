<template>
  <div class="contact-page">
    <h1>联系我们</h1>
    <p>如果您有任何问题或建议，请通过以下方式联系我们。</p>
    <div class="contact-info">
      <p>邮箱：contact@typewriter.com</p>
      <p>电话：123-456-7890</p>
    </div>
  </div>
</template>

<script>
export default {
  name: 'ContactPage'
}
</script>

<style scoped>
.contact-page {
  max-width: 800px;
  margin: 0 auto;
  padding: 20px;
}

.contact-info {
  margin-top: 20px;
  padding: 20px;
  background-color: #f9f9f9;
  border-radius: 8px;
}
</style>