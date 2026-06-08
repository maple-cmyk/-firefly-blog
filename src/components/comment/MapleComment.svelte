<script lang="ts">
  import { onMount } from "svelte";
  import Icon from "@/components/common/Icon.svelte";

  // --- Props ---
  let { postSlug = "", apiUrl = "http://localhost:5000" }: { postSlug: string; apiUrl: string } = $props();

  // --- State ---
  let comments: any[] = [];
  let loading = true;
  let error = "";

  // Auth
  let user: any = null;
  let accessToken = "";
  let showAuthModal = false;
  let authTab: "login" | "register" = "login";
  let authForm = { username: "", email: "", password: "" };
  let authError = "";
  let authLoading = false;

  // Comment form
  let newComment = "";
  let replyTo: { id: number; username: string } | null = null;
  let submitting = false;

  // Like state (tracked locally to avoid refetch)
  let likedIds = new Set<number>();

  // --- Init ---
  onMount(() => {
    const savedToken = localStorage.getItem("maple_comment_token");
    const savedUser = localStorage.getItem("maple_comment_user");
    if (savedToken && savedUser) {
      accessToken = savedToken;
      user = JSON.parse(savedUser);
    }
    fetchComments();
  });

  // --- Helpers ---
  function timeAgo(dateStr: string): string {
    const diff = Date.now() - new Date(dateStr).getTime();
    const sec = Math.floor(diff / 1000);
    if (sec < 60) return "刚刚";
    const min = Math.floor(sec / 60);
    if (min < 60) return `${min} 分钟前`;
    const hr = Math.floor(min / 60);
    if (hr < 24) return `${hr} 小时前`;
    const day = Math.floor(hr / 24);
    if (day < 30) return `${day} 天前`;
    const mon = Math.floor(day / 30);
    return `${mon} 个月前`;
  }

  function authHeader(): Record<string, string> {
    return accessToken ? { Authorization: `Bearer ${accessToken}` } : {};
  }

  // --- API ---
  async function fetchComments() {
    loading = true;
    error = "";
    try {
      const headers: Record<string, string> = { "Content-Type": "application/json" };
      if (accessToken) headers["Authorization"] = `Bearer ${accessToken}`;
      const res = await fetch(`${apiUrl}/api/comments/${encodeURIComponent(postSlug)}`, { headers });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      comments = data.comments || [];
    } catch (e: any) {
      error = "评论加载失败";
      console.error(e);
    } finally {
      loading = false;
    }
  }

  async function handleAuth() {
    authError = "";
    authLoading = true;
    try {
      const endpoint = authTab === "login" ? "login" : "register";
      const body: any = { email: authForm.email, password: authForm.password };
      if (authTab === "register") body.username = authForm.username;

      const res = await fetch(`${apiUrl}/api/auth/${endpoint}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      const data = await res.json();
      if (!res.ok) {
        authError = data.error || "认证失败";
        return;
      }
      user = data.user;
      accessToken = data.access_token;
      localStorage.setItem("maple_comment_token", accessToken);
      localStorage.setItem("maple_comment_user", JSON.stringify(user));
      showAuthModal = false;
      authForm = { username: "", email: "", password: "" };
      fetchComments(); // 刷新以更新点赞状态
    } catch (e: any) {
      authError = "网络错误";
    } finally {
      authLoading = false;
    }
  }

  function logout() {
    user = null;
    accessToken = "";
    localStorage.removeItem("maple_comment_token");
    localStorage.removeItem("maple_comment_user");
    likedIds = new Set();
    fetchComments();
  }

  async function submitComment(parentId?: number) {
    const content = parentId ? newComment : newComment;
    if (!content.trim()) return;
    if (!user) {
      showAuthModal = true;
      return;
    }
    submitting = true;
    try {
      const body: any = { content: content.trim() };
      if (parentId) body.parent_id = parentId;
      const res = await fetch(`${apiUrl}/api/comments/${encodeURIComponent(postSlug)}`, {
        method: "POST",
        headers: { "Content-Type": "application/json", ...authHeader() },
        body: JSON.stringify(body),
      });
      const data = await res.json();
      if (!res.ok) {
        alert(data.error || "发表失败");
        return;
      }
      newComment = "";
      replyTo = null;
      fetchComments();
    } catch (e) {
      alert("网络错误");
    } finally {
      submitting = false;
    }
  }

  async function toggleLike(commentId: number) {
    if (!user) {
      showAuthModal = true;
      return;
    }
    try {
      const res = await fetch(`${apiUrl}/api/likes/${commentId}/toggle`, {
        method: "POST",
        headers: authHeader(),
      });
      const data = await res.json();
      // Update local state
      if (data.liked) {
        likedIds.add(commentId);
      } else {
        likedIds.delete(commentId);
      }
      // Update count in place
      updateLikeCount(comments, commentId, data.likes_count, data.liked);
      comments = comments; // trigger reactivity
    } catch (e) {}
  }

  function updateLikeCount(list: any[], id: number, count: number, liked: boolean) {
    for (const c of list) {
      if (c.id === id) {
        c.likes_count = count;
        c.is_liked = liked;
      }
      if (c.replies) updateLikeCount(c.replies, id, count, liked);
    }
  }

  async function deleteComment(commentId: number) {
    if (!confirm("确定删除这条评论吗？")) return;
    try {
      const res = await fetch(`${apiUrl}/api/comments/${commentId}`, {
        method: "DELETE",
        headers: authHeader(),
      });
      if (res.ok) fetchComments();
    } catch (e) {}
  }

  function gravatar(email: string): string {
    return `https://www.gravatar.com/avatar/${email}?d=mp&s=80`;
  }
</script>

<div class="maple-comments">
  <h3 class="flex items-center gap-2 mb-6 font-bold text-lg text-(--btn-content)">
    <Icon icon="material-symbols:chat-outline" class="text-(--primary)" />
    评论 ({comments.length})
  </h3>

  <!-- Auth Bar -->
  <div class="mb-4 flex items-center justify-between">
    {#if user}
      <div class="flex items-center gap-2 text-sm text-(--content-meta)">
        <span>👋 {user.username}</span>
        <button onclick={logout} class="text-(--primary) hover:underline text-xs">退出</button>
      </div>
    {:else}
      <button
        onclick={() => { showAuthModal = true; authTab = "login"; }}
        class="text-sm text-(--primary) hover:underline"
      >
        登录后参与评论
      </button>
    {/if}
  </div>

  <!-- Comment Form -->
  <div class="mb-6">
    {#if replyTo}
      <div class="text-xs text-(--content-meta) mb-2 flex items-center gap-1">
        回复 @{replyTo.username}
        <button onclick={() => { replyTo = null; newComment = ""; }}
          class="text-(--primary) hover:underline ml-2">取消</button>
      </div>
    {/if}
    <div class="flex gap-3">
      <textarea
        bind:value={newComment}
        placeholder={user ? "写下你的评论..." : "登录后发表评论"}
        rows="3"
        class="flex-1 rounded-xl border border-black/10 dark:border-white/10 bg-black/2 dark:bg-white/5
               px-4 py-3 text-sm resize-none outline-none
               focus:border-(--primary) focus:ring-1 focus:ring-(--primary)
               placeholder:text-black/30 dark:placeholder:text-white/30
               text-(--btn-content)"
        onkeydown={(e) => {
          if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) submitComment(replyTo?.id);
        }}
      ></textarea>
    </div>
    <div class="flex justify-end mt-2">
      <button
        onclick={() => submitComment(replyTo?.id)}
        disabled={!newComment.trim() || submitting || !user}
        class="px-5 py-1.5 rounded-full text-sm font-medium
               bg-(--primary) text-white
               hover:opacity-90 disabled:opacity-40 disabled:cursor-not-allowed
               transition-all"
      >
        {submitting ? "发送中..." : replyTo ? "回复" : "发表评论"}
      </button>
    </div>
  </div>

  <!-- Comments List -->
  {#if loading}
    <div class="space-y-4">
      {#each Array(3) as _}
        <div class="animate-pulse flex gap-3">
          <div class="w-10 h-10 rounded-full bg-black/10 dark:bg-white/10"></div>
          <div class="flex-1 space-y-2">
            <div class="h-4 w-24 bg-black/10 dark:bg-white/10 rounded"></div>
            <div class="h-3 w-full bg-black/5 dark:bg-white/5 rounded"></div>
            <div class="h-3 w-3/4 bg-black/5 dark:bg-white/5 rounded"></div>
          </div>
        </div>
      {/each}
    </div>
  {:else if error}
    <div class="text-center py-8 text-(--content-meta)">
      <p>{error}</p>
      <button onclick={fetchComments} class="text-(--primary) mt-2 hover:underline text-sm">重试</button>
    </div>
  {:else if comments.length === 0}
    <div class="text-center py-12">
      <Icon icon="material-symbols:chat-outline" class="text-4xl text-(--content-meta) mx-auto mb-3 opacity-40" />
      <p class="text-(--content-meta) text-sm">还没有评论，来做第一个留言的人吧～</p>
    </div>
  {:else}
    <div class="space-y-4">
      {#each comments as comment (comment.id)}
        <CommentItem
          {comment}
          {user}
          {likedIds}
          {timeAgo}
          on:like={(e) => toggleLike(e.detail)}
          on:reply={(e) => { replyTo = { id: e.detail.id, username: e.detail.username }; newComment = ""; }}
          on:delete={(e) => deleteComment(e.detail)}
        />
      {/each}
    </div>
  {/if}
</div>

<!-- Comment Item (recursive via manual flattening for simplicity) -->
{#snippet CommentItem(args: { comment: any; user: any; likedIds: Set<number>; timeAgo: Function })}
  {@const { comment, user: currentUser, likedIds: liked, timeAgo: ta } = args}
  <div class="group">
    <div class="flex gap-3">
      <div class="w-10 h-10 rounded-full bg-(--primary)/10 overflow-hidden shrink-0 flex items-center justify-center
                  text-(--primary) text-sm font-bold">
        {comment.user?.username?.[0]?.toUpperCase() || "?"}
      </div>
      <div class="flex-1 min-w-0">
        <div class="flex items-center gap-2 flex-wrap">
          <span class="font-semibold text-sm text-(--btn-content)">{comment.user?.username || "匿名"}</span>
          <span class="text-xs text-(--content-meta)">{ta(comment.created_at)}</span>
        </div>
        <p class="text-sm text-(--btn-content) mt-1 whitespace-pre-wrap break-words">{comment.content}</p>
        <div class="flex items-center gap-4 mt-2">
          <button
            onclick={() => dispatch("like", comment.id)}
            class="flex items-center gap-1 text-xs transition-colors"
            class:text-(--primary)={comment.is_liked || liked.has(comment.id)}
            class:text-(--content-meta)={!comment.is_liked && !liked.has(comment.id)}
          >
            <Icon icon={comment.is_liked || liked.has(comment.id) ? "material-symbols:favorite" : "material-symbols:favorite-outline"}
                  class="text-sm" />
            {comment.likes_count > 0 ? comment.likes_count : ""}
          </button>
          <button
            onclick={() => dispatch("reply", { id: comment.id, username: comment.user?.username })}
            class="text-xs text-(--content-meta) hover:text-(--primary) transition-colors"
          >
            <Icon icon="material-symbols:reply" class="text-sm mr-0.5 inline" />回复
          </button>
          {#if currentUser && currentUser.id === comment.user?.id}
            <button
              onclick={() => dispatch("delete", comment.id)}
              class="text-xs text-(--content-meta) hover:text-red-500 transition-colors opacity-0 group-hover:opacity-100"
            >
              <Icon icon="material-symbols:delete-outline" class="text-sm mr-0.5 inline" />删除
            </button>
          {/if}
        </div>
        <!-- Nested Replies -->
        {#if comment.replies?.length > 0}
          <div class="mt-3 pl-4 border-l-2 border-(--primary)/15 space-y-3">
            {#each comment.replies as reply (reply.id)}
              <CommentItem
                comment={reply}
                user={currentUser}
                likedIds={liked}
                timeAgo={ta}
                on:like
                on:reply
                on:delete
              />
            {/each}
          </div>
        {/if}
      </div>
    </div>
  </div>
{/snippet}

<!-- Auth Modal -->
{#if showAuthModal}
  <!-- svelte-ignore a11y_click_events_have_key_events -->
  <div
    class="fixed inset-0 z-50 flex items-center justify-center bg-black/40 dark:bg-black/60"
    onclick={(e) => { if (e.target === e.currentTarget) showAuthModal = false; }}
    role="dialog"
  >
    <div class="bg-(--card-bg) rounded-2xl p-6 w-full max-w-sm mx-4 shadow-2xl border border-black/5 dark:border-white/5">
      <!-- Tabs -->
      <div class="flex mb-4 border-b border-black/10 dark:border-white/10">
        <button
          onclick={() => { authTab = "login"; authError = ""; }}
          class="flex-1 pb-2 text-sm font-medium transition-colors"
          class:text-(--primary)={authTab === "login"}
          class:text-(--content-meta)={authTab !== "login"}
          class:border-b-2={authTab === "login"}
          class:border-(--primary)={authTab === "login"}
          class:border-transparent={authTab !== "login"}
        >登录</button>
        <button
          onclick={() => { authTab = "register"; authError = ""; }}
          class="flex-1 pb-2 text-sm font-medium transition-colors"
          class:text-(--primary)={authTab === "register"}
          class:text-(--content-meta)={authTab !== "register"}
          class:border-b-2={authTab === "register"}
          class:border-(--primary)={authTab === "register"}
          class:border-transparent={authTab !== "register"}
        >注册</button>
      </div>

      {#if authTab === "register"}
        <input
          bind:value={authForm.username}
          type="text"
          placeholder="用户名"
          class="w-full px-4 py-2.5 mb-3 rounded-xl border border-black/10 dark:border-white/10
                 bg-black/2 dark:bg-white/5 outline-none text-sm text-(--btn-content)
                 focus:border-(--primary)"
        />
      {/if}
      <input
        bind:value={authForm.email}
        type="email"
        placeholder="邮箱"
        class="w-full px-4 py-2.5 mb-3 rounded-xl border border-black/10 dark:border-white/10
               bg-black/2 dark:bg-white/5 outline-none text-sm text-(--btn-content)
               focus:border-(--primary)"
      />
      <input
        bind:value={authForm.password}
        type="password"
        placeholder="密码"
        class="w-full px-4 py-2.5 mb-1 rounded-xl border border-black/10 dark:border-white/10
               bg-black/2 dark:bg-white/5 outline-none text-sm text-(--btn-content)
               focus:border-(--primary)"
        onkeydown={(e) => { if (e.key === "Enter") handleAuth(); }}
      />

      {#if authError}
        <p class="text-red-500 text-xs mt-2">{authError}</p>
      {/if}

      <button
        onclick={handleAuth}
        disabled={authLoading}
        class="w-full mt-4 py-2.5 rounded-xl bg-(--primary) text-white font-medium text-sm
               hover:opacity-90 disabled:opacity-50 transition-all"
      >
        {authLoading ? "请稍候..." : authTab === "login" ? "登录" : "注册"}
      </button>

      <button
        onclick={() => showAuthModal = false}
        class="w-full mt-2 py-2 text-sm text-(--content-meta) hover:text-(--btn-content) transition-colors"
      >
        取消
      </button>
    </div>
  </div>
{/if}

<style>
  .maple-comments {
    /* inherits from parent card-base */
  }
  textarea {
    field-sizing: content;
  }
</style>
