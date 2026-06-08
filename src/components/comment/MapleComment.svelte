<script lang="ts">
  import { onMount } from "svelte";
  import Icon from "@/components/common/Icon.svelte";

  // --- Props ---
  let { postSlug = "", apiUrl = "http://localhost:5000" }: { postSlug: string; apiUrl: string } = $props();

  // --- State ---
  let comments = $state<any[]>([]);
  let loading = $state(true);
  let error = $state("");

  // Guest info
  let guestName = $state("");
  let guestEmail = $state("");
  let guestQQ = $state("");

  // Comment form
  let newComment = $state("");
  let replyTo = $state<{ id: number; username: string } | null>(null);
  let submitting = $state(false);

  // --- Init ---
  onMount(() => {
    const savedName = localStorage.getItem("maple_comment_name");
    const savedEmail = localStorage.getItem("maple_comment_email");
    const savedQQ = localStorage.getItem("maple_comment_qq");
    if (savedName) guestName = savedName;
    if (savedEmail) guestEmail = savedEmail;
    if (savedQQ) guestQQ = savedQQ;
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

  function qqAvatar(qq: string): string {
    return `https://q1.qlogo.cn/g?b=qq&nk=${qq}&s=100`;
  }

  // --- API ---
  async function fetchComments() {
    loading = true;
    error = "";
    try {
      const res = await fetch(`${apiUrl}/api/comments/${encodeURIComponent(postSlug)}`, {
        headers: { "Content-Type": "application/json" },
      });
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

  async function submitComment(parentId?: number) {
    if (!newComment.trim()) return;
    if (!guestName.trim()) {
      alert("请填写昵称");
      return;
    }
    if (!guestEmail.trim()) {
      alert("请填写邮箱");
      return;
    }

    // 保存到 localStorage
    localStorage.setItem("maple_comment_name", guestName.trim());
    localStorage.setItem("maple_comment_email", guestEmail.trim());
    localStorage.setItem("maple_comment_qq", guestQQ.trim());

    submitting = true;
    try {
      const body: any = {
        content: newComment.trim(),
        name: guestName.trim(),
        email: guestEmail.trim(),
      };
      if (guestQQ.trim()) body.qq = guestQQ.trim();
      if (parentId) body.parent_id = parentId;
      const res = await fetch(`${apiUrl}/api/comments/${encodeURIComponent(postSlug)}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
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
</script>

<div class="maple-comments">
  <h3 class="flex items-center gap-2 mb-6 font-bold text-lg text-(--btn-content)">
    <Icon icon="material-symbols:chat-outline" class="text-(--primary)" />
    评论 ({comments.length})
  </h3>

  <!-- Comment Form -->
  <div class="mb-6">
    {#if replyTo}
      <div class="text-xs text-(--content-meta) mb-2 flex items-center gap-1">
        回复 @{replyTo.username}
        <button onclick={() => { replyTo = null; newComment = ""; }}
          class="text-(--primary) hover:underline ml-2">取消</button>
      </div>
    {/if}

    <!-- Name + Email inputs -->
    <div class="flex gap-3 mb-3">
      <input
        value={guestName}
        oninput={(e) => guestName = e.currentTarget.value}
        type="text"
        placeholder="昵称 *"
        class="flex-1 rounded-xl border border-black/10 dark:border-white/10 bg-black/2 dark:bg-white/5
               px-4 py-2.5 text-sm outline-none
               focus:border-(--primary) focus:ring-1 focus:ring-(--primary)
               placeholder:text-black/30 dark:placeholder:text-white/30
               text-(--btn-content)"
      />
      <input
        value={guestEmail}
        oninput={(e) => guestEmail = e.currentTarget.value}
        type="email"
        placeholder="邮箱 *（不会公开）"
        class="flex-1 rounded-xl border border-black/10 dark:border-white/10 bg-black/2 dark:bg-white/5
               px-4 py-2.5 text-sm outline-none
               focus:border-(--primary) focus:ring-1 focus:ring-(--primary)
               placeholder:text-black/30 dark:placeholder:text-white/30
               text-(--btn-content)"
      />
    </div>

    <!-- QQ input (optional) -->
    <div class="mb-3">
      <input
        value={guestQQ}
        oninput={(e) => guestQQ = e.currentTarget.value}
        type="text"
        inputmode="numeric"
        placeholder="QQ 号（选填，用于获取头像）"
        class="w-full rounded-xl border border-black/10 dark:border-white/10 bg-black/2 dark:bg-white/5
               px-4 py-2.5 text-sm outline-none
               focus:border-(--primary) focus:ring-1 focus:ring-(--primary)
               placeholder:text-black/30 dark:placeholder:text-white/30
               text-(--btn-content)"
      />
      {#if guestQQ.trim()}
        <div class="mt-2 flex items-center gap-2 text-xs text-(--content-meta)">
          <img src={qqAvatar(guestQQ.trim())} alt="头像预览" class="w-6 h-6 rounded-full" />
          <span>头像预览</span>
        </div>
      {/if}
    </div>

    <div class="flex gap-3">
      <textarea
        value={newComment}
        oninput={(e) => newComment = e.currentTarget.value}
        placeholder="写下你的评论..."
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
    <div class="flex justify-between items-center mt-2">
      <span class="text-xs text-(--content-meta)">Ctrl+Enter 发送</span>
      <button
        onclick={() => submitComment(replyTo?.id)}
        disabled={!newComment.trim() || submitting || !guestName.trim() || !guestEmail.trim()}
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
          {timeAgo}
          on:reply={(e) => { replyTo = { id: e.detail.id, username: e.detail.username }; newComment = ""; }}
        />
      {/each}
    </div>
  {/if}
</div>

<!-- Comment Item -->
{#snippet CommentItem(args: { comment: any; timeAgo: Function })}
  {@const { comment, timeAgo: ta } = args}
  {@const avatarUrl = comment.user?.avatar_url || ""}
  <div class="group">
    <div class="flex gap-3">
      {#if avatarUrl}
        <img src={avatarUrl} alt={comment.user?.username} class="w-10 h-10 rounded-full shrink-0 object-cover" />
      {:else}
        <div class="w-10 h-10 rounded-full bg-(--primary)/10 overflow-hidden shrink-0 flex items-center justify-center
                    text-(--primary) text-sm font-bold">
          {comment.user?.username?.[0]?.toUpperCase() || "?"}
        </div>
      {/if}
      <div class="flex-1 min-w-0">
        <div class="flex items-center gap-2 flex-wrap">
          <span class="font-semibold text-sm text-(--btn-content)">{comment.user?.username || "匿名"}</span>
          <span class="text-xs text-(--content-meta)">{ta(comment.created_at)}</span>
        </div>
        <p class="text-sm text-(--btn-content) mt-1 whitespace-pre-wrap break-words">{comment.content}</p>
        <div class="flex items-center gap-4 mt-2">
          <span class="flex items-center gap-1 text-xs text-(--content-meta)">
            <Icon icon="material-symbols:favorite-outline" class="text-sm" />
            {comment.likes_count > 0 ? comment.likes_count : ""}
          </span>
          <button
            onclick={() => dispatch("reply", { id: comment.id, username: comment.user?.username })}
            class="text-xs text-(--content-meta) hover:text-(--primary) transition-colors"
          >
            <Icon icon="material-symbols:reply" class="text-sm mr-0.5 inline" />回复
          </button>
        </div>
        {#if comment.replies?.length > 0}
          <div class="mt-3 pl-4 border-l-2 border-(--primary)/15 space-y-3">
            {#each comment.replies as reply (reply.id)}
              <CommentItem
                comment={reply}
                timeAgo={ta}
                on:reply
              />
            {/each}
          </div>
        {/if}
      </div>
    </div>
  </div>
{/snippet}

<style>
  .maple-comments {
  }
  textarea {
    field-sizing: content;
  }
</style>
