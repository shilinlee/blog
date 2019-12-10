# 6.1 简介

如果程序运行失败仅被认为是几个预期的结果之一。对于那些将运行失败看作是预期结果的函数，它们会返回一个额外的返回值，通常是最后一个来传递错误信息。如果导致失败的原因只有一个，额外的返回值可以是一个布尔值，通常被命名为ok。比如，当从一个`map`查询一个结果时，可以通过额外的布尔值判断是否成功：

```go
if v, ok := m["key"]; ok {
    return v
}
```

但是导致失败的原因通常不止一种，很多时候用户希望了解更多的错误信息。如果只是用简单的布尔类型的状态值将不能满足这个要求。在C语言中，默认采用一个整数类型的`errno`来表达错误，这样就可以根据需要定义多种错误类型。在Go语言中，`syscall.Errno`就是对应C语言中`errno`类型的错误。在`syscall`包中的接口，如果有返回错误的话，底层也是`syscall.Errno`错误类型。

比如我们通过`syscall`包的接口来修改文件的模式时，如果遇到错误我们可以通过将`err`强制断言为`syscall.Errno`错误类型来处理：

```go
err := syscall.Chmod(":invalid path:", 0666)
if err != nil {
    log.Fatal(err.(syscall.Errno))
}
```

我们还可以进一步地通过类型查询或类型断言来获取底层真实的错误类型，这样就可以获取更详细的错误信息。不过一般情况下我们并不关心错误在底层的表达方式，我们只需要知道它是一个错误就可以了。当返回的错误值不是`nil`时，我们可以通过调用`error`接口类型的`Error`方法来获得字符串类型的错误信息。

在Go语言中，**错误被认为是一种可以预期的结果**；**而异常则是一种非预期的结果**，发生异常可能表示程序中存在BUG或发生了其它不可控的问题。Go语言推荐使用`recover`函数将内部异常转为错误处理，这使得用户可以真正的关心业务相关的错误处理。

如果某个接口简单地将所有普通的错误当做异常抛出，将会使错误信息杂乱且没有价值。就像在`main`函数中直接捕获全部一样，是没有意义的：

```go
func main() {
    defer func() {
        if r := recover(); r != nil {
            log.Fatal(r)
        }
    }()

    ...
}
```

捕获异常不是最终的目的。如果异常不可预测，直接输出异常信息是最好的处理方式。

# 6.2 错误处理策略

让我们演示一个文件复制的例子：函数需要打开两个文件，然后将其中一个文件的内容复制到另一个文件：

```go
func CopyFile(dstName, srcName string) (written int64, err error) {
    src, err := os.Open(srcName)
    if err != nil {
        return
    }

    dst, err := os.Create(dstName)
    if err != nil {
        return
    }

    written, err = io.Copy(dst, src)
    dst.Close()
    src.Close()
    return
}
```

上面的代码虽然能够工作，但是隐藏一个bug。如果第一个`os.Open`调用成功，但是第二个`os.Create`调用失败，那么会在没有释放`src`文件资源的情况下返回。虽然我们可以通过在第二个返回语句前添加`src.Close()`调用来修复这个BUG；但是当代码变得复杂时，类似的问题将很难被发现和修复。我们可以通过`defer`语句来确保每个被正常打开的文件都能被正常关闭：

```go
func CopyFile(dstName, srcName string) (written int64, err error) {
    src, err := os.Open(srcName)
    if err != nil {
        return
    }
    defer src.Close()

    dst, err := os.Create(dstName)
    if err != nil {
        return
    }
    defer dst.Close()

    return io.Copy(dst, src)
}
```

`defer`语句可以让我们在打开文件时马上思考如何关闭文件。不管函数如何返回，文件关闭语句始终会被执行。同时`defer`语句可以保证，即使`io.Copy`发生了异常，文件依然可以安全地关闭。

前文我们说到，Go语言中的导出函数一般不抛出异常，一个未受控的异常可以看作是程序的BUG。但是对于那些提供类似Web服务的框架而言；它们经常需要接入第三方的中间件。因为第三方的中间件是否存在BUG是否会抛出异常，Web框架本身是不能确定的。为了提高系统的稳定性，Web框架一般会通过`recover`来防御性地捕获所有处理流程中可能产生的异常，然后将异常转为普通的错误返回。

让我们以JSON解析器为例，说明recover的使用场景。考虑到JSON解析器的复杂性，即使某个语言解析器目前工作正常，也无法肯定它没有漏洞。因此，当某个异常出现时，我们不会选择让解析器崩溃，而是会将panic异常当作普通的解析错误，并附加额外信息提醒用户报告此错误。

```go
func ParseJSON(input string) (s *Syntax, err error) {
    defer func() {
        if p := recover(); p != nil {
            err = fmt.Errorf("JSON: internal error: %v", p)
        }
    }()
    // ...parser...
}
```

标准库中的`json`包，在内部递归解析JSON数据的时候如果遇到错误，会通过抛出异常的方式来快速跳出深度嵌套的函数调用，然后由最外一级的接口通过`recover`捕获`panic`，然后返回相应的错误信息。

Go语言库的实现习惯: 即使在包内部使用了`panic`，但是在导出函数时会被转化为明确的错误值。